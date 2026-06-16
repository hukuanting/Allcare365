param(
    [switch]$SeedBulk,
    [switch]$ExportContract,
    [string]$BaseUrl = "",
    [string]$Token = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-GuardScript {
    param(
        [string]$Name,
        [string]$Script,
        [string[]]$Arguments = @()
    )

    Write-Host ""
    Write-Host "==> $Name"
    & powershell -ExecutionPolicy Bypass -File $Script @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$singlePatientArgs = @()
if ($ExportContract) {
    $singlePatientArgs += "-ExportContract"
}
if ($BaseUrl) {
    $singlePatientArgs += @("-BaseUrl", $BaseUrl)
}
if ($Token) {
    $singlePatientArgs += @("-Token", $Token)
}

$bulkArgs = @()
if ($SeedBulk) {
    $bulkArgs += "-Seed"
}

Invoke-GuardScript "ONC Single Patient API baseline" ".\verify_onc_single_patient_api.ps1" $singlePatientArgs
Invoke-GuardScript "ONC Bulk Data STU2 baseline" ".\verify_onc_bulk_data_stu2.ps1" $bulkArgs
Invoke-GuardScript "ONC SMART visual inspection baseline" ".\verify_onc_visual_inspection.ps1"

Write-Host ""
Write-Host "ONC g10 full local certification baseline passed."
