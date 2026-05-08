param(
    [string]$PythonExe = "python",
    [string]$Version = "1.0.0",
    [string]$IsccExe = "",
    [switch]$Sign,
    [string]$SigntoolExe = "",
    [string]$PfxPath = "",
    [string]$PfxPassword = "",
    [string]$CertThumbprint = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$ReleaseRoot = Join-Path $ProjectRoot "release"
$PackageName = "heater-zoning-optimizer-v$Version-windows"
$PackageDir = Join-Path $ReleaseRoot $PackageName
$SampleDir = Join-Path $PackageDir "sample-data"
$ZipPath = Join-Path $ReleaseRoot "$PackageName.zip"
$InstallerDir = Join-Path $ReleaseRoot "installer"
$PackageReadme = Join-Path $ProjectRoot "packaging\windows\README.txt"

if (-not $IsccExe) {
    $Candidates = @(
        "C:\Users\use\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            $IsccExe = $Candidate
            break
        }
    }
}

& $PythonExe -m PyInstaller --clean --noconfirm heater_zoning_optimizer.spec

if (Test-Path $PackageDir) {
    Remove-Item $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $SampleDir -Force | Out-Null

Copy-Item "$ProjectRoot\dist\heater-zoning-optimizer.exe" "$PackageDir\heater-zoning-optimizer.exe" -Force
Copy-Item "$ProjectRoot\data\sample_profile.csv" "$SampleDir\sample_profile.csv" -Force
Copy-Item $PackageReadme "$PackageDir\README.txt" -Force

$Hash = (Get-FileHash "$PackageDir\heater-zoning-optimizer.exe" -Algorithm SHA256).Hash
@"
heater-zoning-optimizer.exe
SHA256: $Hash
"@ | Set-Content "$PackageDir\SHA256.txt" -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path "$PackageDir\*" -DestinationPath $ZipPath -Force

if (-not (Test-Path $InstallerDir)) {
    New-Item -ItemType Directory -Path $InstallerDir -Force | Out-Null
}

if (Test-Path $IsccExe) {
    & $IsccExe "$ProjectRoot\installer\heater_zoning_optimizer.iss"
}

if ($Sign) {
    & "$ProjectRoot\scripts\sign_release.ps1" `
        -Targets @(
            "$ProjectRoot\dist\heater-zoning-optimizer.exe",
            "$InstallerDir\heater-zoning-optimizer-setup-v1.0.0.exe"
        ) `
        -SigntoolExe $SigntoolExe `
        -PfxPath $PfxPath `
        -PfxPassword $PfxPassword `
        -CertThumbprint $CertThumbprint
}

Write-Host ""
Write-Host "Release package completed."
Write-Host "Folder: $PackageDir"
Write-Host "Zip:    $ZipPath"
if (Test-Path $IsccExe) {
    Write-Host "Setup:  $InstallerDir"
}
