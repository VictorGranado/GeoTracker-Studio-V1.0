$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& (Join-Path $PSScriptRoot 'Build_Windows.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $PSScriptRoot 'Build_Installer.ps1')
exit $LASTEXITCODE
