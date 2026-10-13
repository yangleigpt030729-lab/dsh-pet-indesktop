<# Run using Windows PowerShell 5.1 before any build/install work. #>
param([string]$SourceRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$companionScripts = Get-ChildItem -LiteralPath (Join-Path $SourceRoot 'scripts') -Filter '*.ps1' -File
$strictUtf8 = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false, $true
foreach ($companionScript in $companionScripts) {
    $bytes = [System.IO.File]::ReadAllBytes($companionScript.FullName)
    if ($bytes.Length -lt 3 -or $bytes[0] -ne 0xEF -or $bytes[1] -ne 0xBB -or $bytes[2] -ne 0xBF) {
        throw "UTF-8 BOM missing: $($companionScript.Name). Re-download the reviewed source ZIP."
    }
    $null = $strictUtf8.GetString($bytes, 3, $bytes.Length - 3)
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $companionScript.FullName, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count -gt 0) {
        foreach ($parseError in $parseErrors) {
            Write-Host "$($companionScript.Name):$($parseError.Extent.StartLineNumber): $($parseError.Message)"
        }
        throw "PowerShell parse failed: $($companionScript.Name)"
    }
    Write-Host "PowerShell $($PSVersionTable.PSVersion) parse PASS: $($companionScript.Name)"
}
if (-not $companionScripts) { throw 'No PowerShell scripts found.' }
