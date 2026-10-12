<# Creates a source-test environment, not a final EXE release. Never reads keys. #>
param([switch]$RunFocusedTests)
$ErrorActionPreference = 'Stop'
$companionRoot = Split-Path -Parent $PSScriptRoot
Set-Location $companionRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
& py -3.11 -c "import struct,sys; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8, 'Python 3.11 x64 required'"
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 x64 with the Windows py launcher' }
& py -3.11 -m venv .venv-win10
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
$companionPython = Join-Path $companionRoot '.venv-win10\Scripts\python.exe'
& $companionPython -m pip install -r requirements.txt -c packaging\constraints-win10-companion.txt
if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency installation failed; do not bypass TLS or pins' }
& $companionPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed' }
& $companionPython -c "import sys,struct,PySide6;from PySide6.QtCore import qVersion;print(sys.version);print(struct.calcsize('P')*8,PySide6.__version__,qVersion())"
if ($RunFocusedTests) {
    $companionOldQpa = $env:QT_QPA_PLATFORM
    $env:QT_QPA_PLATFORM = 'offscreen'
    try {
        & $companionPython -m pytest -q tests\test_companion_proactive_hardening.py tests\test_companion_proactive_state.py tests\test_companion_proactive_service.py tests\test_companion_proactive_failures.py tests\test_companion_proactive_network.py tests\test_companion_proactive_ui.py tests\test_companion_proactive_schedule.py tests\test_companion_acceptance_package.py tests\test_companion_chat.py
        if ($LASTEXITCODE -ne 0) { throw 'Focused tests failed' }
    } finally {
        $env:QT_QPA_PLATFORM = $companionOldQpa
    }
}
Write-Host 'Prepared source environment. For the desktop test, follow docs\WINDOWS10-COMPANION-ACCEPTANCE.md.'
