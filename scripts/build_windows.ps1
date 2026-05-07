param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& $PythonExe -m PyInstaller --clean --noconfirm heater_zoning_optimizer.spec

Write-Host ""
Write-Host "Build completed."
Write-Host "Check the dist directory:"
Write-Host "$ProjectRoot\\dist"
