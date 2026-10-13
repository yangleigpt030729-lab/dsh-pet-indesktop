"""Read-only portable validation and fresh staging; never package a running data directory."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import stat
import struct
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.package_companion_test import credential_check, TEXT
from scripts.slim_bundle import REQUIRED_GLOBS, verify_required, find_forbidden

EXE = 'dsh-pet-standalone-webm-chat.exe'
APP_ID = '{662C52E9-287D-43C4-90DE-4A0B9061C7C4}'  # Fixed across all companion installer upgrades.
VERSION = '1.0.0'
REQUIRED = (*REQUIRED_GLOBS, '_internal/python3??.dll',
            '_internal/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-*.exe',
            '_internal/assets/characters/shenshen/videos/manifest.json',
            '_internal/assets/characters/shenshen/videos/*/*.webm',
            '_internal/LICENSE', '_internal/THIRD_PARTY_NOTICES.md')
STATIC_AUDIO = frozenset('_internal/assets/sounds/'+s for s in (
    'duck/Ya1.mp3', 'duck/Ya2.mp3', 'click.wav', 'agent/start.wav', 'agent/error.wav', 'agent/done.wav'))
PRIVATE_DIRS = {'sessions', 'logs', 'screenshots', 'self_talk_voice', 'voice_chime_cache',
                'voice_cache', '.git', '.venv', '__pycache__'}
PRIVATE_NAMES = {'config.json', 'secrets.json', 'settings.lock', 'file_eaten_stats.json',
                 'proactive_screen_memory.json', 'companion-migration.pending', 'credentials.json',
                 'api_keys.json', 'tokens.json', 'settings.json', 'user_settings.json'}
MAX_BYTES = 2*1024**3
MAX_FILES = 32000


def safe_name(name):
    name = name.replace('\\', '/')
    parts = name.rstrip('/').split('/')
    if (not parts or any(not p or p in ('.', '..') or p[-1:] in (' ', '.') or ':' in p
                         or any(ord(c)<32 for c in p) or any(c in p for c in '<>"|?*') for p in parts)
            or name.startswith('/')
            or any(re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p, re.I) for p in parts)):
        raise ValueError('Unsafe Windows archive path rejected')
    return '/'.join(parts)


def private_path(name):
    path = PurePosixPath(name.lower())
    base = path.name
    return (bool(set(path.parts) & PRIVATE_DIRS) or base in PRIVATE_NAMES
            or base.startswith(('.env', 'config-slot-', 'todo_items'))
            or (base.startswith('config') and base.endswith('.json'))
            or '.sqlite' in base or base.endswith(('.db', '.db-wal', '.db-shm', '.db-journal', '.log', '.jsonl', '.pfx', '.p12', '.key'))
            or (base.endswith('.pem') and name.lower() != '_internal/certifi/cacert.pem')
            or (base.endswith(('.mp3', '.wav')) and name not in STATIC_AUDIO))


def check_layout(names):
    if EXE not in names or any(n != EXE and not n.startswith('_internal/') for n in names):
        raise ValueError('Expected the webm-chat EXE and complete _internal only')
    if find_forbidden(names) or verify_required(names, REQUIRED):
        raise ValueError('Required runtime/resources missing or forbidden build dependency present')


def check_pe(header):
    try:
        offset = struct.unpack_from('<I', header, 60)[0]
        machine = struct.unpack_from('<H', header, offset+4)[0]
        magic = struct.unpack_from('<H', header, offset+24)[0]
        subsystem = struct.unpack_from('<H', header, offset+24+68)[0]
        valid = (header[:2] == b'MZ' and header[offset:offset+4] == b'PE\0\0'
                 and machine == 0x8664 and magic == 0x20b and subsystem == 2)
    except (struct.error, IndexError):
        valid = False
    if not valid:
        raise ValueError('Expected Windows x64 windowed executable')


def _digest(stream):
    digest, count = hashlib.sha256(), 0
    while data := stream.read(1024*1024):
        digest.update(data)
        count += len(data)
    return {'size': count, 'sha256': digest.hexdigest()}


def _scan_text(name, data):
    if name.lower().endswith('.pem'):
        if b'-----BEGIN CERTIFICATE-----' not in data or re.search(rb'-----BEGIN[^\r\n]*PRIVATE KEY-----', data):
            raise ValueError('TLS certificate payload contains invalid or private key material')
        return
    if PurePosixPath(name).suffix.lower() in TEXT:
        try:
            clean = data.removeprefix(b'\xef\xbb\xbf')
            credential_check(name.lower(), clean)
            if name.lower().endswith('.json'):
                def extra_credentials(value):
                    if isinstance(value, dict):
                        for key, item in value.items():
                            if str(key).lower() in {'authorization', 'token', 'password', 'client_secret', 'private_key', 'deepseek_api_key'} and item:
                                raise ValueError('Private credential field rejected')
                            extra_credentials(item)
                    elif isinstance(value, list):
                        for item in value:
                            extra_credentials(item)
                extra_credentials(json.loads(clean))
        except (UnicodeError, ValueError):
            raise ValueError('Invalid text or credential-like payload rejected; values not logged') from None


def _zip_entries(archive):
    infos = archive.infolist()
    if len(infos)>MAX_FILES or sum(i.file_size for i in infos)>MAX_BYTES:
        raise ValueError('Portable archive exceeds bounded release limits')
    entries, seen = [], set()
    for info in infos:
        name = safe_name(info.filename)
        key = name.casefold()
        mode = info.external_attr >> 16
        if (key in seen or info.flag_bits & 1
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))):
            raise ValueError('Duplicate, encrypted or linked archive entry rejected')
        seen.add(key)
        entries.append((name, info))
    wrapper = 'dsh-pet-standalone-webm-chat/'
    wrapped = any(n == wrapper+EXE for n, _ in entries)
    files = {}
    for name, info in entries:
        if wrapped:
            if name == wrapper.rstrip('/') and info.is_dir():
                continue
            if not name.startswith(wrapper):
                raise ValueError('Mixed portable roots rejected')
            name = name[len(wrapper):]
        if private_path(name):
            raise ValueError('Private user data path rejected; names not logged')
        if not info.is_dir():
            files[name] = info
    check_layout(files)
    return files


def stage(zip_path, directory, manifest_path):
    zip_path, directory, manifest_path = map(Path, (zip_path, directory, manifest_path))
    if directory.exists() or manifest_path.exists():
        raise FileExistsError('Payload and manifest must be new; existing outputs are preserved')
    if manifest_path.resolve().is_relative_to(directory.resolve()):
        raise ValueError('Manifest must stay outside installable payload')
    report = {'format': 1, 'app_id': APP_ID, 'version': VERSION, 'exe': EXE, 'files': {}}
    with zip_path.open('rb') as stream:
        report['portable_sha256'] = _digest(stream)['sha256']
    with zipfile.ZipFile(zip_path) as archive:
        entries = _zip_entries(archive)
        # All names, structure, PE and credentials pass before creating a payload directory.
        with archive.open(entries[EXE]) as stream:
            check_pe(stream.read(4096))
        for name, info in sorted(entries.items()):
            with archive.open(info) as stream:
                report['files'][name] = _digest(stream)
            if PurePosixPath(name).suffix.lower() in TEXT | {'.pem'}:
                if info.file_size > 8*1024**2:
                    raise ValueError('Text payload exceeds bounded credential-scan limit')
                _scan_text(name, archive.read(info))
        directory.mkdir(parents=True, exist_ok=False)
        for name, info in sorted(entries.items()):
            target = directory.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open('xb') as dest:
                while data := source.read(1024*1024):
                    dest.write(data)
            with target.open('rb') as stream:
                if _digest(stream) != report['files'][name]:
                    raise ValueError('Payload changed during staging; build stopped')
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, sort_keys=True, indent=2)
    return report


def verify_directory(directory, manifest_path):
    directory = Path(directory)
    if directory.is_symlink() or getattr(directory, 'is_junction', lambda: False)() or not directory.is_dir():
        raise ValueError('Expected an unlinked payload directory')
    report = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if not isinstance(report, dict):
        raise ValueError('Invalid payload manifest object')
    if (report.get('app_id'), report.get('version'), report.get('exe'), report.get('format')) != (APP_ID, VERSION, EXE, 1):
        raise ValueError('Payload manifest release identity mismatch')
    names = {}
    for path in directory.rglob('*'):
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Linked payload path rejected')
        name = safe_name(path.relative_to(directory).as_posix())
        if private_path(name):
            raise ValueError('Private data added after staging')
        if path.is_file():
            key = name.casefold()
            if key in names:
                raise ValueError('Case-colliding payload paths')
            names[key] = name
    check_layout(names.values())
    if set(names.values()) != set(report['files']):
        raise ValueError('Payload file manifest mismatch')
    for name in names.values():
        path = directory/name
        with path.open('rb') as stream:
            if _digest(stream) != report['files'][name]:
                raise ValueError('Payload checksum mismatch')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path)
    parser.add_argument('--stage', type=Path)
    parser.add_argument('--verify-dir', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.verify_dir:
            report = verify_directory(args.verify_dir, args.manifest)
        elif args.zip and args.stage:
            report = stage(args.zip, args.stage, args.manifest)
        else:
            parser.error('use --zip/--stage or --verify-dir')
        print(f"PASS: {len(report['files'])} payload files; version {VERSION}; complete runtime; no private data paths")
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
