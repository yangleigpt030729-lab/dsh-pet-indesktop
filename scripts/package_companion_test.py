"""Deterministic, credential-free source acceptance ZIP; not an EXE cross-build."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile

DIRS = {'pet', 'assets', 'scripts', 'packaging', 'tests', 'docs', 'integrations', '.agents', '.github'}
ROOT_FILES = {'README.md', 'LICENSE', 'requirements.txt', 'pyproject.toml', 'AGENTS.md', 'CONTEXT.md', 'DEVELOPMENT_PLAN_WIN10.md', '.gitignore'}
SKIP_DIRS = {'__pycache__', 'node_modules', '.venv', '.git', '.scratch', '.research', 'sessions'}
TEXT = {'.py', '.md', '.txt', '.json', '.toml', '.ini', '.yaml', '.yml', '.js', '.mjs', '.ps1', '.qss'}
PREFIX = 'dsh-pet-companion-win10/'
MANIFEST = 'ACCEPTANCE-SHA256.json'


def allowed(relative):
    path = PurePosixPath(relative)
    name = path.name.lower()
    return (not any(part in SKIP_DIRS for part in path.parts)
            and (path.parts[0] in DIRS or relative in ROOT_FILES)
            and not (name.startswith(('.env', 'config-slot-', 'todo_items')) or name == 'config.json'
                     or name in {'file_eaten_stats.json', 'proactive_screen_memory.json', 'companion-migration.pending', 'settings.lock'}
                     or '.sqlite3' in name or name == 'build_variant.py'
                     or path.suffix.lower() in {'.db', '.log', '.jsonl', '.pyc', '.pfx', '.pem', '.key', '.zip', '.whl'}))


def credential_check(relative, data):
    if PurePosixPath(relative).suffix.lower() not in TEXT:
        return
    text = data.decode('utf-8')
    if (re.search(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}', text)
            or re.search(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----(?:\s|\\n)+[A-Za-z0-9+/=]{32,}', text)):
        raise ValueError('Credential-like source content rejected; no values logged')
    if relative.endswith('.json'):
        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if str(key).lower() in {'api_key', 'apikey', 'vision_api_key', 'access_token', 'refresh_token', 'secret'} and item:
                        raise ValueError('Nonempty credential field rejected; no values logged')
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        check(json.loads(text))


def source_files(root):
    if (root/'.git').exists():
        # A real checkout never packages untracked local notes/configuration.
        paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    else:
        # GitHub Download ZIP contains no Git metadata; the same allowlist applies.
        paths = [p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()]
    for relative in sorted(set(p for p in paths if p and allowed(p))):
        path = root/relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Source symlinks are not accepted')
        yield relative, path


def write_member(archive, relative, data):
    info = zipfile.ZipInfo(PREFIX+relative, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)


def build(root, output):
    root, output = Path(root), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        candidate = Path(temporary)/'source.zip'
        with zipfile.ZipFile(candidate, 'w') as archive:
            for relative, path in source_files(root):
                data = path.read_bytes()
                credential_check(relative, data)
                hashes[relative] = hashlib.sha256(data).hexdigest()
                write_member(archive, relative, data)
            if not hashes or 'requirements.txt' not in hashes:
                raise ValueError('Expected a complete source root')
            write_member(archive, MANIFEST, json.dumps({'format':1, 'files':hashes}, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8'))
        verify(candidate)
        os.replace(candidate, output)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def verify(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive paths')
        manifest = json.loads(archive.read(PREFIX+MANIFEST))
        expected = {PREFIX+p for p in manifest['files']} | {PREFIX+MANIFEST}
        if set(names) != expected:
            raise ValueError('Archive manifest mismatch')
        for relative, digest in manifest['files'].items():
            if '..' in PurePosixPath(relative).parts or not allowed(relative):
                raise ValueError('Unexpected source path')
            data = archive.read(PREFIX+relative)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('Source checksum mismatch')
            credential_check(relative, data)
    return len(manifest['files'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        print(f'PASS: {verify(args.verify)} source checksums; no credential files')
    elif args.output:
        print('SHA256:', build(args.root, args.output))
    else:
        parser.error('specify --output or --verify')
