"""Static preflight is portable; native Parser.ParseFile remains a Windows gate."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['build_onedir.ps1', 'build_windows_companion.ps1',
                                  'prepare_windows_companion.ps1', 'check_powershell_scripts.ps1'])
def test_official_powershell_scripts_are_utf8_bom(name):
    data = (ROOT / 'scripts' / name).read_bytes()
    assert data.startswith(b'\xef\xbb\xbf'), f'{name}: PowerShell 5.1 requires BOM for UTF-8'
    data.decode('utf-8-sig', errors='strict')


def test_preparse_is_native_and_preserves_security_build_gates():
    check = (ROOT / 'scripts/check_powershell_scripts.ps1').read_text(encoding='utf-8-sig')
    assert '[System.Management.Automation.Language.Parser]::ParseFile' in check
    assert '$parseErrors.Count -gt 0' in check and 'UTF-8 BOM missing' in check
    wrapper = (ROOT / 'scripts/build_windows_companion.ps1').read_text(encoding='utf-8-sig')
    assert wrapper.index('check_powershell_scripts.ps1') < wrapper.index('New-Item')
    assert wrapper.count('check_powershell_scripts.ps1') == 2
    build = (ROOT / 'scripts/build_onedir.ps1').read_text(encoding='utf-8-sig')
    for gate in ('check_powershell_scripts.ps1', 'slim_bundle.py', 'check_bundle_encoding.py',
                 'verify_bundle_qt.py', '--windowed', 'Wait-SmokeWindow'):
        assert gate in build


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows PowerShell 5.1 parser required')
@pytest.mark.parametrize('fault', ['none', 'no_bom', 'syntax'])
def test_native_powershell51_preparse_reports_real_failures(tmp_path, fault):
    stage = tmp_path / 'scripts'
    stage.mkdir()
    data = '# UTF-8 中文\nWrite-Host "OK"\n'
    if fault == 'syntax':
        data += 'Write-Host "unterminated\n'
    (stage / 'sample.ps1').write_text(data, encoding='utf-8' if fault == 'no_bom' else 'utf-8-sig')
    command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               str(ROOT / 'scripts/check_powershell_scripts.ps1'), '-SourceRoot', str(tmp_path)]
    result = subprocess.run(command, capture_output=True, timeout=30)
    assert (result.returncode == 0) == (fault == 'none'), result.stdout + result.stderr
