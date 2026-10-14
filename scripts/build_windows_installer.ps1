<# Build a per-user offline installer from a fresh current-source onedir build. PowerShell 5.1. #>
param(
    [string]$WorkDir = 'D:\Code\FishCompanionBuildV101',
    [string]$OutputDir = 'D:\Code\FishReleaseV101',
    [string]$PythonExe = 'D:\Code\FishVenv312\Scripts\python.exe',
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
$installerOutput = [IO.Path]::GetFullPath($OutputDir)
$installerNativeWork = [IO.Path]::GetFullPath($WorkDir)
foreach ($candidate in @($installerOutput, $installerNativeWork)) {
    if (Test-Path -LiteralPath $candidate) { throw 'OutputDir and WorkDir must both be NEW. Old releases/builds are never overwritten.' }
}
$installerDirectories = @($installerSource, $installerOutput, $installerNativeWork)
for ($i = 0; $i -lt $installerDirectories.Count; $i++) {
    for ($j = $i + 1; $j -lt $installerDirectories.Count; $j++) {
        $left = $installerDirectories[$i].TrimEnd('\')
        $right = $installerDirectories[$j].TrimEnd('\')
        if ($left -eq $right -or $left.StartsWith($right + '\', [StringComparison]::OrdinalIgnoreCase) -or $right.StartsWith($left + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'SourceRoot, WorkDir and OutputDir must be separate, non-nested directories.'
        }
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
& $PythonExe -X utf8 -c "import sys,struct; assert sys.platform=='win32' and struct.calcsize('P')==8, 'Windows x64 build Python required'"
if ($LASTEXITCODE -ne 0) { throw 'Use Windows Python 3.11/3.12 x64. No environment is changed; the build creates a separate new pinned venv.' }
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
    # No PortableZip parameter: the current source MUST be built, with all existing gates.
    Push-Location $installerSource
    try {
        & (Join-Path $PSScriptRoot 'build_windows_companion.ps1') -PythonExe $PythonExe -WorkDir $installerNativeWork
    } finally { Pop-Location }
    $installerHelpers = Join-Path $installerNativeWork 'dsh-pet-companion-win10'
    $installerBuildPython = Join-Path $installerNativeWork 'build-venv\Scripts\python.exe'
    $installerInput = Join-Path $installerHelpers 'dist-onedir\dsh-pet-standalone-webm-chat-portable.zip'
    $installerSourceReceipt = Join-Path $installerOutput 'source-build-manifest.json'
    & $installerBuildPython -X utf8 (Join-Path $installerHelpers 'scripts\verify_installer_source.py') --source $installerSource --work $installerNativeWork --receipt $installerSourceReceipt
    if ($LASTEXITCODE -ne 0) { throw 'Fresh source/frozen module/portable ZIP provenance gate failed.' }
    # build_windows_companion.ps1 invokes package_companion_test.py and native preparse.
    # The new build venv has the pinned PyInstaller/pefile/edge-tts dependencies.
    $PythonExe = $installerBuildPython
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
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_installer_source.py') --source $installerSource --work $installerNativeWork --receipt $installerSourceReceipt --verify
    if ($LASTEXITCODE -ne 0) { throw 'Source build changed before Inno compilation.' }
    & $IsccExe @installerArguments
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed. Retain this new output directory and build.log.' }
    & $PythonExe -X utf8 (Join-Path $installerHelpers 'scripts\verify_installer_payload.py') --verify-dir $installerPayload --manifest $installerManifest
    if ($LASTEXITCODE -ne 0) { throw 'Payload changed during compilation; do not distribute this build.' }
    $installerSetup = Join-Path $installerOutput '大肥鱼桌面宠物_Setup_v1.0.1.exe'
    if (-not (Test-Path -LiteralPath $installerSetup -PathType Leaf)) { throw 'Expected Setup output missing.' }
    $installerSignature = Get-AuthenticodeSignature -FilePath $installerSetup
    if ($installerSigned -and $installerSignature.Status -ne 'Valid') { throw 'Requested code signature was not verified; do not distribute.' }
    $installerHash = (Get-FileHash -LiteralPath $installerSetup -Algorithm SHA256).Hash
    $installerMetadata = [ordered]@{
        version = '1.0.1'; file = $installerSetup; bytes = (Get-Item -LiteralPath $installerSetup).Length
        source_build_manifest_sha256 = (Get-FileHash -LiteralPath $installerSourceReceipt -Algorithm SHA256).Hash
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
    Write-Host 'Distribute ONLY the Setup EXE. Retain the separate native WorkDir, source receipt and logs as build evidence. Native install/upgrade/uninstall acceptance is still required.'
} catch {
    Write-Host ('BUILD FAILED: ' + $_.Exception.Message)
    Write-Host ('Preserve new output directory for diagnosis: ' + $installerOutput)
    throw
} finally {
    if ($installerTranscript) { Stop-Transcript | Out-Null }
}
