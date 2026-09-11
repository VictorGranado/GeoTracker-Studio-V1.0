$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$distExe = Join-Path $PSScriptRoot 'dist\GeoTracker Studio v1.0\GeoTracker Studio.exe'
if (-not (Test-Path $distExe)) {
    throw 'Windows app build not found. Run .\Build_Windows.ps1 first.'
}

function Find-InnoSetupCompiler {
    # 1) Already available through PATH.
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -and (Test-Path $cmd.Source)) {
        return $cmd.Source
    }

    # 2) Common machine-wide and per-user installation locations.
    $commonCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
    ) | Where-Object { $_ -and (Test-Path $_) }

    if ($commonCandidates) {
        return $commonCandidates
    }

    # 3) Ask Windows where Inno Setup was installed.
    $uninstallKeys = @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )

    foreach ($key in $uninstallKeys) {
        $apps = Get-ItemProperty $key -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -like 'Inno Setup 6*' }

        foreach ($app in $apps) {
            if ($app.InstallLocation) {
                $candidate = Join-Path $app.InstallLocation 'ISCC.exe'
                if (Test-Path $candidate) {
                    return $candidate
                }
            }
        }
    }

    return $null
}

$iscc = Find-InnoSetupCompiler

if (-not $iscc) {
    Write-Host ''
    Write-Host 'Inno Setup 6 is installed but ISCC.exe could not be located.' -ForegroundColor Yellow
    Write-Host 'Try this PowerShell command to locate it:'
    Write-Host "  Get-ChildItem `$env:LOCALAPPDATA,`$env:ProgramFiles,`${env:ProgramFiles(x86)} -Filter ISCC.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 10 FullName"
    Write-Host ''
    Write-Host 'If that command finds ISCC.exe, you can compile manually with:'
    Write-Host "  & 'FULL_PATH_TO_ISCC.exe' '.\installer\GeoTrackerStudio.iss'"
    exit 2
}

Write-Host ''
Write-Host 'GeoTracker Studio v1.0 - Installer Build' -ForegroundColor Cyan
Write-Host '----------------------------------------'
Write-Host "Using Inno Setup compiler: $iscc" -ForegroundColor DarkGray

& $iscc (Join-Path $PSScriptRoot 'installer\GeoTrackerStudio.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }

Write-Host ''
Write-Host 'Installer complete:' -ForegroundColor Green
Write-Host (Join-Path $PSScriptRoot 'installer_output\GeoTracker Studio v1.0 Setup.exe')
