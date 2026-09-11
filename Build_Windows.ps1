$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host ''
Write-Host 'GeoTracker Studio v1.0 - Windows Release Build' -ForegroundColor Cyan
Write-Host '------------------------------------------------'

python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; release build cancelled.' }

# Remove stale release output so the executable being tested is definitely the new build.
if (Test-Path 'build') { Remove-Item -Recurse -Force 'build' }
if (Test-Path 'dist') { Remove-Item -Recurse -Force 'dist' }

python -m PyInstaller --noconfirm --clean GeoTrackerStudio.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host ''
Write-Host 'Build complete:' -ForegroundColor Green
Write-Host (Join-Path $PSScriptRoot 'dist\GeoTracker Studio v1.0\GeoTracker Studio.exe')
