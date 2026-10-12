from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_safe_build_reuses_existing_onedir_with_explicit_interpreter():
    wrapper = (ROOT/'scripts/build_windows_companion.ps1').read_text(encoding='utf-8-sig')
    original = (ROOT/'scripts/build_onedir.ps1').read_text(encoding='utf-8-sig')
    assert 'package_companion_test.py' in wrapper and 'build_onedir.ps1' in wrapper
    assert '-NoStopRunning' in wrapper and '-SmokeAcceptance' in wrapper
    assert 'constraints-win10-companion.txt' in wrapper
    assert '-X utf8 -m pip' in wrapper
    assert '[string]$PythonExe' in original
    assert '& $PythonExe -X utf8 -m PyInstaller' in original
    assert '--companion-acceptance' in original
    assert 'Get-FileHash' in wrapper


def test_source_module_acceptance_entry_supports_fake_without_keys(tmp_path):
    import os
    result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pet',
                             '--companion-acceptance', '--data-dir', str(tmp_path/'acceptance'),
                             '--auto-close-seconds', '12'], cwd=ROOT,
                            env={**os.environ, 'PET_FRAMESEQ': '0', 'QT_QPA_PLATFORM': 'offscreen'},
                            capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'FAKE: synthetic proactive bubble displayed' in result.stdout
