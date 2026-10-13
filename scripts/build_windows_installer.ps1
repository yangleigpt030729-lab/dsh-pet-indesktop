<# Build a per-user offline installer from a validated portable ZIP. PowerShell 5.1. #>
param(
    [Parameter(Mandatory=$true)][string]$PortableZip,
    [string]$OutputDir = 'D:\Code\FishReleaseV100',
    [string]$PythonExe = 'D:\Code\FishCompanionBuildExperience20261013\build-venv\Scripts\python.exe',
    [string]$IsccExe = '',
    [string]$SignToolExe = '',
    [string]$CertificateThumbprint = '',
    [string]$TimestampUrl = 'https://timestamp.digicert.com'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$installerSource = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'check_powershell_scripts.ps1') -SourceRoot $installerSource
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Windows x64 and 64-bit PowerShell are required.'
}
$installerInput = (Resolve-Path -LiteralPath $PortableZip -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath $installerInput -PathType Leaf) -or [IO.Path]::GetExtension($installerInput) -ne '.zip') {
    throw 'PortableZip must be the original validated portable ZIP, not a running pet folder.'
}
$installerOutput = [IO.Path]::GetFullPath($OutputDir)
if (Test-Path -LiteralPath $installerOutput) { throw 'OutputDir already exists. Use a NEW directory; old releases are never overwritten.' }
foreach ($protected in @($installerSource, (Split-Path -Parent $installerInput))) {
    if ($installerOutput.StartsWith($protected + '\', [StringComparison]::OrdinalIgnoreCase) -or $installerOutput -eq $protected) {
        throw 'OutputDir must be outside the source and portable input directories.'
    }
}
if (-not $IsccExe) {
    $installerCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
    )
    $installerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($installerCommand) { $installerCandidates += $installerCommand.Source }
    $IsccExe = $installerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $IsccExe -or -not (Test-Path -LiteralPath $IsccExe -PathType Leaf)) {
    throw 'Install Inno Setup 6.5 or newer from https://jrsoftware.org/isdl.php, or specify -IsccExe. No software is auto-downloaded.'
}
$IsccExe = (Resolve-Path -LiteralPath $IsccExe).Path
$installerCompilerVersion = (Get-Item -LiteralPath $IsccExe).VersionInfo.ProductVersion
if ($installerCompilerVersion -notmatch '^6\.(\d+)' -or [int]$Matches[1] -lt 5) {
    throw 'Inno Setup 6.5+ is required for the bundled official Chinese translation and x64os policy.'
}
& $PythonExe -X utf8 -c "import sys,struct,PyInstaller,pefile,edge_tts; assert sys.platform=='win32' and struct.calcsize('P')==8, 'Windows x64 build Python required'"
if ($LASTEXITCODE -ne 0) { throw 'Use the successful portable build-venv Python; PyInstaller/pefile/edge-tts are required. No environment is changed.' }
$installerSigned = [bool]$SignToolExe -or [bool]$CertificateThumbprint
if ($installerSigned) {
    if (-not (Test-Path -LiteralPath $SignToolExe -PathType Leaf) -or $CertificateThumbprint -notmatch '^[A-Fa-f0-9]{40}$' -or $TimestampUrl -notmatch '^https://[A-Za-z0-9./:_-]+$') {
        throw 'Signing requires an explicit signtool.exe, public certificate thumbprint and HTTPS timestamp URL; never pass a PFX password.'
    }
    $SignToolExe = (Resolve-Path -LiteralPath $SignToolExe).Path
    $installerCertificate = Get-Item -LiteralPath ('Cert:\CurrentUser\My\' + $CertificateThumbprint) -ErrorAction Stop
    if (-not $installerCertificate.HasPrivateKey) { throw 'The chosen CurrentUser code-signing certificate has no private key.' }
}
New-Item -ItemType Directory -Path $installerOutput -ErrorAction Stop | Out-Null
$installerWork = Join-Path $installerOutput 'build'
New-Item -ItemType Directory -Path $installerWork -ErrorAction Stop | Out-Null
$installerTranscript = $false
try {
    Start-Transcript -Path (Join-Path $installerOutput 'build.log') -NoClobber | Out-Null
    $installerTranscript = $true
    Push-Location $installerSource
    try {
        & $PythonExe -X utf8 scripts\package_companion_test.py --output (Join-Path $installerWork 'reviewed-source.zip')
        if ($LASTEXITCODE -ne 0) { throw 'Safe source-helper packaging failed.' }
    } finally { Pop-Location }
    Expand-Archive -LiteralPath (Join-Path $installerWork 'reviewed-source.zip') -DestinationPath $installerWork
    $installerHelpers = Join-Path $installerWork 'dsh-pet-companion-win10'
    & (Join-Path $installerHelpers 'scripts\check_powershell_scripts.ps1') -SourceRoot $installerHelpers
    $installerPayload = Join-Path $installerWork 'payload'
    $installerManifest = Join-Path $installerOutput 'payload-manifest.json'
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_installer_payload.py') --zip $installerInput --stage $installerPayload --manifest $installerManifest
    if ($LASTEXITCODE -ne 0) { throw 'Portable structure/privacy/Windows PE validation failed; no installer will be produced.' }
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_bundle_tts.py') --app-dir $installerPayload
    if ($LASTEXITCODE -ne 0) { throw 'Frozen TTS archive gate failed.' }
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_bundle_qt.py') --internal (Join-Path $installerPayload '_internal')
    if ($LASTEXITCODE -ne 0) { throw 'Native Qt DLL chain gate failed.' }
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\check_bundle_encoding.py') --dir $installerPayload
    if ($LASTEXITCODE -ne 0) { throw 'Frozen code/resource UTF-8 gate failed.' }
    $installerExe = Join-Path $installerPayload 'dsh-pet-standalone-webm-chat.exe'
    Add-Type -AssemblyName System.Drawing
    $installerIconPath = Join-Path $installerWork 'application.ico'
    $installerIcon = [Drawing.Icon]::ExtractAssociatedIcon($installerExe)
    if (-not $installerIcon) { throw 'Validated EXE application icon could not be extracted.' }
    $installerIconStream = [IO.File]::Open($installerIconPath, [IO.FileMode]::CreateNew)
    try { $installerIcon.Save($installerIconStream) } finally { $installerIconStream.Dispose(); $installerIcon.Dispose() }
    $installerArguments = @(
        ('/DPayloadDir=' + $installerPayload),
        ('/DReleaseDir=' + $installerOutput),
        ('/DInstallerIcon=' + $installerIconPath)
    )
    if ($installerSigned) {
        $installerArguments += '/DSignToolName=CompanionAuthenticode'
        $installerArguments += ('/SCompanionAuthenticode=$q' + $SignToolExe + '$q sign /fd SHA256 /sha1 ' + $CertificateThumbprint + ' /tr ' + $TimestampUrl + ' /td SHA256 $f')
    }
    $installerArguments += (Join-Path $installerHelpers 'packaging\dafeiyu-v1.iss')
    # Verify once more immediately before compiling; no user files copied from the source into payload.
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_installer_payload.py') --verify-dir $installerPayload --manifest $installerManifest
    if ($LASTEXITCODE -ne 0) { throw 'Payload changed before compilation.' }
    & $IsccExe @installerArguments
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed. Retain this new output directory and build.log.' }
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_installer_payload.py') --verify-dir $installerPayload --manifest $installerManifest
    if ($LASTEXITCODE -ne 0) { throw 'Payload changed during compilation; do not distribute this build.' }
    $installerSetup = Join-Path $installerOutput '大肥鱼桌面宠物_Setup_v1.0.0.exe'
    if (-not (Test-Path -LiteralPath $installerSetup -PathType Leaf)) { throw 'Expected Setup output missing.' }
    $installerSignature = Get-AuthenticodeSignature -FilePath $installerSetup
    if ($installerSigned -and $installerSignature.Status -ne 'Valid') { throw 'Requested code signature was not verified; do not distribute.' }
    $installerHash = (Get-FileHash -LiteralPath $installerSetup -Algorithm SHA256).Hash
    $installerMetadata = [ordered]@{
        version = '1.0.0'; file = $installerSetup; bytes = (Get-Item -LiteralPath $installerSetup).Length
        sha256 = $installerHash; portable_sha256 = (Get-FileHash -LiteralPath $installerInput -Algorithm SHA256).Hash
        iscc_version = $installerCompilerVersion; signature_status = [string]$installerSignature.Status
        native_install_acceptance = 'NOT TESTED by build script'
    }
    $installerMetadata | ConvertTo-Json | Out-File (Join-Path $installerOutput 'setup-manifest.json') -Encoding utf8 -NoClobber
    Write-Host ('Setup: ' + $installerSetup)
    Write-Host ('Bytes: ' + $installerMetadata.bytes)
    Write-Host ('SHA256: ' + $installerHash)
    Write-Host ('Signature: ' + $installerSignature.Status)
    if (-not $installerSigned) { Write-Host 'Unsigned test installer: Windows SmartScreen may show an unknown publisher warning.' }
    Write-Host 'Distribute ONLY the Setup EXE, not build/ or reviewed-source.zip. Native install/upgrade/uninstall acceptance is still required.'
} catch {
    Write-Host ('BUILD FAILED: ' + $_.Exception.Message)
    Write-Host ('Preserve new output directory for diagnosis: ' + $installerOutput)
    throw
} finally {
    if ($installerTranscript) { Stop-Transcript | Out-Null }
}
