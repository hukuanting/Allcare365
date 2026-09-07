# Optional ONC/Inferno public-endpoint helper. Normal system startup does not
# invoke this script.
$ErrorActionPreference = "Stop"

$runtimeDir = Join-Path $PSScriptRoot "tmp\onc-cloudflare"
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

$logPath = Join-Path $runtimeDir "cloudflared-quick-tunnel.log"
if (Test-Path $logPath) {
    Remove-Item $logPath -Force
}

function Show-OncUrls {
    param([string] $TunnelUrl)

    $publicBaseUrl = $TunnelUrl.TrimEnd("/")
    $oidcIssuer = "$publicBaseUrl/o/"
    $fhirBaseUrl = "$publicBaseUrl/fhir/R4"
    $metadataUrl = "$fhirBaseUrl/metadata"
    $smartLaunchTestUrl = "$publicBaseUrl/smart-launch-test/"
    $envPath = Join-Path $runtimeDir "cloudflare-current-url.env"

    @(
        "PUBLIC_BASE_URL=$publicBaseUrl"
        "OIDC_ISS_ENDPOINT=$oidcIssuer"
        "ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com"
        "FHIR_BASE_URL=$fhirBaseUrl"
        "FHIR_METADATA_URL=$metadataUrl"
        "SMART_LAUNCH_TEST_URL=$smartLaunchTestUrl"
    ) | Set-Content -Path $envPath -Encoding ASCII

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Cloudflare Quick Tunnel URL detected" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Copy these values for ONC / Inferno testing:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PUBLIC_BASE_URL:"
    Write-Host "  $publicBaseUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "FHIR Base URL:"
    Write-Host "  $fhirBaseUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "FHIR Metadata / CapabilityStatement:"
    Write-Host "  $metadataUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "SMART EHR Launch Test Page:"
    Write-Host "  $smartLaunchTestUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "OIDC Issuer:"
    Write-Host "  $oidcIssuer" -ForegroundColor Green
    Write-Host ""
    Write-Host "Local .env values for this run:"
    Write-Host "  PUBLIC_BASE_URL=$publicBaseUrl" -ForegroundColor Green
    Write-Host "  OIDC_ISS_ENDPOINT=$oidcIssuer" -ForegroundColor Green
    Write-Host "  ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com" -ForegroundColor Green
    Write-Host ""
    Write-Host "These values were also written to:" -ForegroundColor Yellow
    Write-Host "  $envPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "If your SMART authorization link uses an old tunnel URL, update .env with" -ForegroundColor Yellow
    Write-Host "these values, restart the backend, and restart the Inferno test session." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Important: quick tunnel URLs can change each time you restart cloudflared." -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    if ($env:AUTO_OPEN_SMART_LAUNCH_TEST -ne "false") {
        Write-Host "Opening SMART EHR Launch Test Page..." -ForegroundColor Yellow
        Start-Process $smartLaunchTestUrl
    }
}

Write-Host "Starting free Cloudflare quick tunnel for http://localhost:8000 ..."
Write-Host "Waiting for the trycloudflare.com URL..."
Write-Host ""

$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = "cloudflared"
$processInfo.Arguments = "tunnel --url http://localhost:8000 --protocol http2 --edge-ip-version 4 --loglevel info"
$processInfo.UseShellExecute = $false
$processInfo.RedirectStandardError = $true
$processInfo.RedirectStandardOutput = $false

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processInfo
[void] $process.Start()

$printedUrl = $false

while (-not $process.HasExited) {
    $line = $process.StandardError.ReadLine()
    if ($null -eq $line) {
        Start-Sleep -Milliseconds 200
        continue
    }

    Add-Content -Path $logPath -Value $line
    Write-Host $line

    if (-not $printedUrl -and $line -match "https://[A-Za-z0-9-]+\.trycloudflare\.com") {
        $printedUrl = $true
        Show-OncUrls $Matches[0]
    }
}

exit $process.ExitCode
