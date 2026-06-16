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
Invoke-GuardStep "SMART visual inspection contracts" @("manage.py", "test", "tests.test_smart_visual_inspection_contracts")
Invoke-GuardStep "Register SMART visual inspection clients" @("manage.py", "setup_smart_visual_inspection_clients")
Invoke-GuardStep "Register EHR launch clients" @("manage.py", "setup_ehr_app")

Write-Host ""
Write-Host "ONC Visual Inspection and Attestation local guard passed."
