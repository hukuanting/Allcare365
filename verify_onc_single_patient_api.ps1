param(
    [string]$BaseUrl = "",
    [string]$Token = "",
    [switch]$ExportContract
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

function Invoke-GuardStep {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-GuardStep "Django system check" @("manage.py", "check")
Invoke-GuardStep "US Core projection contracts" @("-m", "unittest", "tests.test_uscore_projection_contracts")

if ($ExportContract) {
    Invoke-GuardStep "Export g10 certification contract" @("manage.py", "export_g10_certification_contract")
}

if ($BaseUrl) {
    $preflightArgs = @("inferno_preflight_validator.py", "--base-url", $BaseUrl)
    if ($Token) {
        $preflightArgs += @("--token", $Token)
    }
    Invoke-GuardStep "Live Inferno preflight" $preflightArgs
}

Write-Host ""
Write-Host "ONC Single Patient API local guard passed."
