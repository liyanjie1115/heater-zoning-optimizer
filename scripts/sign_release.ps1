param(
    [string[]]$Targets = @(),
    [string]$SigntoolExe = "",
    [string]$PfxPath = "",
    [string]$PfxPassword = "",
    [string]$CertThumbprint = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [switch]$SkipIfUnavailable
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Resolve-Signtool {
    param([string]$Requested)

    if ($Requested -and (Test-Path $Requested)) {
        return $Requested
    }

    $candidates = @(
        "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

if (-not $Targets -or $Targets.Count -eq 0) {
    $Targets = @(
        "$ProjectRoot\dist\heater-zoning-optimizer.exe",
        "$ProjectRoot\release\installer\heater-zoning-optimizer-setup-v1.0.0.exe"
    )
}

$Signtool = Resolve-Signtool -Requested $SigntoolExe
if (-not $Signtool) {
    if ($SkipIfUnavailable) {
        Write-Warning "signtool.exe not found. Skipping signing."
        exit 0
    }
    throw "signtool.exe not found. Install Windows SDK / App Certification Kit or pass -SigntoolExe."
}

if (-not $PfxPath -and -not $CertThumbprint) {
    if ($SkipIfUnavailable) {
        Write-Warning "No code signing certificate configured. Skipping signing."
        exit 0
    }
    throw "No certificate configured. Pass -PfxPath or -CertThumbprint."
}

foreach ($target in $Targets) {
    if (-not (Test-Path $target)) {
        throw "Target not found: $target"
    }

    $arguments = @(
        "sign",
        "/fd", "SHA256",
        "/td", "SHA256",
        "/tr", $TimestampUrl
    )

    if ($PfxPath) {
        $arguments += @("/f", $PfxPath)
        if ($PfxPassword) {
            $arguments += @("/p", $PfxPassword)
        }
    } else {
        $arguments += @("/sha1", $CertThumbprint)
    }

    $arguments += $target
    & $Signtool @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Signing failed: $target"
    }
    Write-Host "Signed: $target"
}
