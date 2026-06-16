@echo off
echo Starting Backend...
start "Backend" cmd /v:on /k "set PYTHONIOENCODING=utf-8 && venv\Scripts\activate && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm start"

echo Starting Cloudflare Tunnel...
where cloudflared >nul 2>nul
if errorlevel 1 (
    echo cloudflared was not found in PATH.
    echo Install Cloudflare Tunnel first, then re-run this script:
    echo   winget install --id Cloudflare.cloudflared
    echo.
    echo Backend and frontend have been started, but no public tunnel was opened.
) else (
    start "Cloudflare Tunnel" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start_cloudflare_quick_tunnel.ps1"
)

echo System startup initiated.
pause
