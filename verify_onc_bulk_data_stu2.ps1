param(
    [switch]$Seed
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
Invoke-GuardStep "Bulk Data STU2 contracts" @("-m", "unittest", "tests.test_bulk_data_stu2_contracts")

if ($Seed) {
    Invoke-GuardStep "Register Inferno Bulk client" @("manage.py", "setup_bulk_inferno_client")
    Invoke-GuardStep "Seed Bulk Group patients" @("manage.py", "seed_bulk_group")
}

Write-Host ""
Write-Host "ONC Bulk Data STU2 local guard passed."
