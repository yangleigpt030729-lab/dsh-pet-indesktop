<# Clean Windows x64 Chat onedir build. No existing venv/data/output is replaced. #>
param(
    [string]$PythonExe = 'D:\Code\FishVenv312\Scripts\python.exe',
    [string]$WorkDir = 'D:\Code\FishCompanionBuild'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$companionSource = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'check_powershell_scripts.ps1') -SourceRoot $companionSource
$companionWork = [System.IO.Path]::GetFullPath($WorkDir)
if (Test-Path $companionWork) { throw 'WorkDir must be new; retain old builds for rollback.' }
if ($companionWork.StartsWith($companionSource + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'WorkDir must be outside the source checkout.'
}
if (Get-Process -Name 'dsh-pet-standalone-webm-chat' -ErrorAction SilentlyContinue) {
    throw 'Please exit the existing Chat EXE first; this workflow never kills it.'
}
& $PythonExe -X utf8 -c "import sys,struct; assert sys.platform=='win32' and struct.calcsize('P')==8 and sys.version_info[:2] in [(3,11),(3,12)], 'Windows Python 3.11/3.12 x64 required'"
if ($LASTEXITCODE -ne 0) { throw 'Unsupported build interpreter.' }
New-Item -ItemType Directory -Path $companionWork | Out-Null
Set-Location $companionSource
# Packages tracked source only (or the allowlisted contents of GitHub Download ZIP).
# Credential-like fields, private databases, sessions and logs are rejected/excluded.
$companionZip = Join-Path $companionWork 'reviewed-source.zip'
& $PythonExe -X utf8 scripts\package_companion_test.py --output $companionZip
if ($LASTEXITCODE -ne 0) { throw 'Safe source packaging failed.' }
Expand-Archive -Path $companionZip -DestinationPath $companionWork
$companionStage = Join-Path $companionWork 'dsh-pet-companion-win10'
& $PythonExe -X utf8 -m venv (Join-Path $companionWork 'build-venv')
if ($LASTEXITCODE -ne 0) { throw 'Clean build venv creation failed.' }
$companionPython = Join-Path $companionWork 'build-venv\Scripts\python.exe'
Set-Location $companionStage
& (Join-Path $companionStage 'scripts\check_powershell_scripts.ps1') -SourceRoot $companionStage
& $companionPython -X utf8 -m pip install -r requirements.txt -r packaging\requirements-companion-build.txt -c packaging\constraints-win10-companion.txt
if ($LASTEXITCODE -ne 0) { throw 'Pinned installation failed; do not bypass TLS or pins.' }
& $companionPython -X utf8 -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
& $companionPython -X utf8 -c "import PySide6; assert PySide6.__version__=='6.8.3', 'Win10 Qt pin mismatch'"
if ($LASTEXITCODE -ne 0) { throw 'Qt profile mismatch.' }
& $companionPython -X utf8 -m pip freeze | Out-File (Join-Path $companionWork 'build-dependencies.txt') -Encoding utf8
& (Join-Path $companionStage 'scripts\build_onedir.ps1') -Variant webm-chat -PythonExe $companionPython -NoStopRunning -SmokeAcceptance
if ($LASTEXITCODE -ne 0) { throw 'Native onedir build failed.' }
$companionOutput = Join-Path $companionStage 'dist-onedir\dsh-pet-standalone-webm-chat-portable.zip'
Get-FileHash $companionOutput -Algorithm SHA256 | Format-List
Write-Host "Portable output: $companionOutput"
Write-Host 'Ship the complete onedir folder/ZIP, never the EXE alone. No real API key is included.'
