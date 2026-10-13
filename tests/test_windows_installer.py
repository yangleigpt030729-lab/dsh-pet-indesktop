"""Installer payload safety is real filesystem/ZIP validation, never a Windows PASS."""
import json
import struct
import zipfile
from pathlib import Path

import pytest
from scripts import verify_installer_payload as payload

ROOT = Path(__file__).resolve().parents[1]


def pe(machine=0x8664, subsystem=2):
    data = bytearray(256)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, machine)
    struct.pack_into('<H', data, 88, 0x20b)
    struct.pack_into('<H', data, 88+68, subsystem)
    return bytes(data)


def files():
    result = {payload.EXE: pe(), '_internal/LICENSE':b'License', '_internal/THIRD_PARTY_NOTICES.md':b'Attribution',
              '_internal/assets/characters/shenshen/videos/manifest.json':b'{}',
              '_internal/assets/characters/shenshen/videos/idle/a.webm':b'synthetic animation',
              '_internal/python312.dll':b'dll', '_internal/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe':b'exe'}
    for glob in payload.REQUIRED:
        name = glob.replace('*.exe', payload.EXE).replace('*.dll','runtime.dll').replace('*','test').replace('?','1')
        result.setdefault(name,b'synthetic dependency')
    return result


def archive(tmp_path, contents=None, prefix=''):
    output = tmp_path/'portable.zip'
    with zipfile.ZipFile(output,'w') as z:
        for name,data in (contents or files()).items():
            z.writestr(prefix+name,data)
    return output


@pytest.mark.parametrize('prefix', ['', 'dsh-pet-standalone-webm-chat/'])
def test_real_root_zip_is_complete_and_never_changes_source(tmp_path, prefix):
    source = archive(tmp_path,prefix=prefix)
    original = source.read_bytes()
    dest, manifest = tmp_path/'new-payload', tmp_path/'payload-manifest.json'
    report = payload.stage(source,dest,manifest)
    assert source.read_bytes() == original
    assert (dest/payload.EXE).read_bytes() == pe()
    assert report['version'] == '1.0.0' and report['files'][payload.EXE]['size'] == len(pe())
    assert payload.verify_directory(dest,manifest) == report
    assert 'voice_chime_cache' not in str(report)


@pytest.mark.parametrize('name', [
    'config.json','_internal/config-slot-1.json','_internal/sessions/chat.json',
    '_internal/companion_memory.sqlite3','_internal/companion_memory.sqlite3-wal',
    '_internal/config_override.json','_internal/credentials.json','_internal/private.db','_internal/private.db-wal','_internal/private.db-shm','_internal/private.db-journal','_internal/pet.log','_internal/screenshots/private.png',
    '_internal/self_talk_voice/secret.mp3','_internal/voice_chime_cache/a.mp3',
    '_internal/.env','_internal/secrets.json','_internal/private.pfx',
    '_internal/assets/sounds/private.mp3','_internal/todo_items.json',
    '../escaped.exe','/absolute.exe','C:/absolute.exe','_internal/file:stream',
    '_internal/CON.txt','_internal/trailing.','_internal/trailing ',
])
def test_reject_private_or_unsafe_zip_before_extracting(tmp_path,name):
    content=files(); content[name]=b'synthetic private data'
    dest=tmp_path/'payload'
    with pytest.raises(ValueError):
        payload.stage(archive(tmp_path,content),dest,tmp_path/'manifest.json')
    assert not dest.exists()


@pytest.mark.parametrize('fault',['duplicate','case','symlink','encrypted','missing','x86','console','credential','wrapped_mix'])
def test_invalid_payload_stops_without_partial_destination(tmp_path,fault):
    content=files()
    if fault=='missing': content={k:v for k,v in content.items() if not k.startswith('_internal/python3')}
    elif fault=='x86': content[payload.EXE]=pe(machine=0x14c)
    elif fault=='console': content[payload.EXE]=pe(subsystem=3)
    elif fault=='credential': content['_internal/assets/characters/shenshen/videos/manifest.json']=json.dumps({'authorization':'synthetic-private-token'}).encode()
    elif fault=='wrapped_mix': content['dsh-pet-standalone-webm-chat/extra.txt']=b'extra'
    source=archive(tmp_path,content)
    if fault in ('duplicate','case','symlink','encrypted'):
        with zipfile.ZipFile(source,'a') as z:
            if fault=='duplicate':
                with pytest.warns(UserWarning): z.writestr(payload.EXE,pe())
            elif fault=='case': z.writestr(payload.EXE.upper(),pe())
            else:
                entry=zipfile.ZipInfo('_internal/unsafe')
                entry.create_system=3
                entry.external_attr=(0o120777 << 16) if fault=='symlink' else (0o100644 << 16)
                z.writestr(entry,b'synthetic')
        if fault=='encrypted':
            raw=bytearray(source.read_bytes())
            # Mark the last central-directory entry encrypted; reject before reading.
            index=raw.rfind(b'PK\x01\x02'); raw[index+8] |= 1; source.write_bytes(raw)
    with pytest.raises(ValueError): payload.stage(source,tmp_path/'payload',tmp_path/'manifest.json')
    assert not (tmp_path/'payload').exists()


def test_existing_output_and_tamper_are_rejected(tmp_path):
    source=archive(tmp_path)
    dest,manifest=tmp_path/'payload',tmp_path/'manifest.json'
    payload.stage(source,dest,manifest)
    before=(dest/payload.EXE).read_bytes()
    with pytest.raises(FileExistsError): payload.stage(source,dest,tmp_path/'different.json')
    assert (dest/payload.EXE).read_bytes()==before
    (dest/payload.EXE).write_bytes(before+b'tampered')
    with pytest.raises(ValueError): payload.verify_directory(dest,manifest)


def test_installer_contract_and_bom():
    iss=(ROOT/'packaging/dafeiyu-v1.iss').read_text(encoding='utf-8-sig')
    script=(ROOT/'scripts/build_windows_installer.ps1').read_bytes()
    assert script.startswith(b'\xef\xbb\xbf')
    ps=script.decode('utf-8-sig')
    for phrase in ('PrivilegesRequired=lowest','AppVersion=1.0.0','DefaultDirName={localappdata}\\Programs\\DaFeiYuDesktopPet',
                   'CloseApplications=no','RestartApplications=no','ArchitecturesAllowed=x64os','PrepareToInstall',
                   'InitializeUninstall','dsh-pet-standalone-webm-chat.exe','大肥鱼桌面宠物_Setup_v1.0.0'):
        assert phrase in iss
    assert '[UninstallDelete]' not in iss and '[Registry]' not in iss
    assert 'taskkill' not in ps.lower() and 'Stop-Process' not in ps and 'TerminateProcess' not in iss
    for name in ('verify_installer_payload.py','package_companion_test.py','verify_bundle_tts.py',
                 'verify_bundle_qt.py','check_bundle_encoding.py','check_powershell_scripts.ps1','Get-FileHash'):
        assert name in ps
    assert 'Test-Path' in ps and 'Start-Transcript' in ps and 'Stop-Transcript' in ps
    assert 'ignoreversion recursesubdirs createallsubdirs' in iss
    assert 'Flags: unchecked; Check: HasExistingAutostart' in iss
    assert 'UsePreviousAppDir=no' in iss and 'RegDeleteValue' in iss


def test_fixed_identity_data_safety_and_signing_contract():
    iss=(ROOT/'packaging/dafeiyu-v1.iss').read_text(encoding='utf-8-sig')
    assert payload.APP_ID in iss and payload.VERSION in iss
    for operation in ('DelTree(', 'DeleteFile(', 'ForceCloseApplications=', '{userappdata}', '{commonappdata}'):
        assert operation not in iss
    assert "RegQueryStringValue(HKCU64, OwnUninstallKey, 'InstallLocation'" in iss
    assert 'PetsRunning(Failed)' in iss and 'DetectionFailed := True' in iss
    assert "WizardIsTaskSelected('migrateautostart') and HasExistingAutostart" in iss
    assert 'Pos(Lowercase(OwnExe), Lowercase(Command)) > 0' in iss
    assert '#ifdef SignToolName' in iss and 'SignedUninstaller=yes' in iss
    ps=(ROOT/'scripts/build_windows_installer.ps1').read_text(encoding='utf-8-sig')
    assert 'CurrentUser\\My\\' in ps and 'Get-AuthenticodeSignature' in ps
    assert 'unknown publisher' in ps and 'No environment is changed' in ps


def test_all_verified_static_sounds_and_tls_certificate_are_allowed(tmp_path):
    content=files()
    for name in payload.STATIC_AUDIO: content[name]=b'synthetic original asset'
    content['_internal/certifi/cacert.pem']=b'-----BEGIN CERTIFICATE-----\nsynthetic public certificate'
    assert payload.stage(archive(tmp_path,content),tmp_path/'payload',tmp_path/'manifest.json')


@pytest.mark.parametrize('fault',['added_private','added_extra','symlink','identity'])
def test_post_staging_changes_are_rejected(tmp_path,fault):
    dest,manifest=tmp_path/'payload',tmp_path/'manifest.json'
    payload.stage(archive(tmp_path),dest,manifest)
    if fault=='identity':
        raw=json.loads(manifest.read_text());raw['version']='9.9.9';manifest.write_text(json.dumps(raw))
    elif fault=='symlink':
        try: (dest/'_internal'/'linked').symlink_to(dest/payload.EXE)
        except OSError: pytest.skip('host does not allow symlinks')
    else: (dest/'_internal'/('config.json' if fault=='added_private' else 'extra.dll')).write_bytes(b'added')
    with pytest.raises(ValueError): payload.verify_directory(dest,manifest)


@pytest.mark.skipif(__import__('sys').platform != 'win32',reason='Windows PowerShell 5.1 native entry required')
def test_native_wrapper_refuses_existing_output_without_changes(tmp_path):
    import subprocess
    source=archive(tmp_path)
    output=tmp_path/'existing';output.mkdir();marker=output/'keep.txt';marker.write_bytes(b'keep')
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        str(ROOT/'scripts/build_windows_installer.ps1'),'-PortableZip',str(source),'-OutputDir',str(output)],
        capture_output=True,timeout=60)
    assert result.returncode != 0
    assert marker.read_bytes()==b'keep' and list(output.iterdir()) == [marker]


@pytest.mark.skipif(__import__('sys').platform != 'win32',reason='Windows ISCC native compilation required')
def test_native_inno_compiles_synthetic_payload_only(tmp_path):
    import os
    import shutil
    import subprocess
    compiler=shutil.which('ISCC.exe') or str(Path(os.environ.get('ProgramFiles(x86)',''))/'Inno Setup 6'/'ISCC.exe')
    if not Path(compiler).is_file(): pytest.skip('Inno Setup 6.5+ not installed on this test host')
    source=archive(tmp_path)
    dest=tmp_path/'payload';payload.stage(source,dest,tmp_path/'manifest.json')
    output=tmp_path/'compiled';output.mkdir()
    result=subprocess.run([compiler,'/DPayloadDir='+str(dest),'/DReleaseDir='+str(output),
        '/DInstallerIcon='+str(ROOT/'assets/icon.ico'),str(ROOT/'packaging/dafeiyu-v1.iss')],
        capture_output=True,timeout=120)
    assert result.returncode==0, result.stdout+result.stderr
    assert (output/'大肥鱼桌面宠物_Setup_v1.0.0.exe').stat().st_size>0
    # Compiler/contract smoke only. Never install or launch this synthetic executable.


def test_root_symlink_and_private_key_in_tls_ca_are_rejected(tmp_path):
    source=archive(tmp_path)
    dest,manifest=tmp_path/'payload',tmp_path/'manifest.json'
    payload.stage(source,dest,manifest)
    moved=tmp_path/'moved';dest.rename(moved)
    try: dest.symlink_to(moved, target_is_directory=True)
    except OSError: pytest.skip('host does not allow directory symlinks')
    with pytest.raises(ValueError): payload.verify_directory(dest,manifest)
    content=files();content['_internal/certifi/cacert.pem']=b'-----BEGIN PRIVATE KEY-----\n' + b'A'*64
    with pytest.raises(ValueError): payload.stage(archive(tmp_path,content),tmp_path/'other',tmp_path/'other.json')


def test_uppercase_json_still_rejects_private_api_fields(tmp_path):
    content=files()
    content['_internal/extra.JSON']=json.dumps({'api_key':'synthetic-private-credential'}).encode()
    with pytest.raises(ValueError):
        payload.stage(archive(tmp_path,content),tmp_path/'payload',tmp_path/'manifest.json')
    assert not (tmp_path/'payload').exists()
