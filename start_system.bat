@chcp 65001 >nul
@echo off
title Allcare365 - Full Stack Server
color 0E

echo.
echo  ██╗  ██╗███████╗ █████╗ ██╗  ████████╗██╗  ██╗     ██████╗  ██████╗ ███████╗
echo  ██║  ██║██╔════╝██╔══██╗██║  ╚══██╔══╝██║  ██║     ╚════██╗██╔════╝ ██╔════╝
echo  ███████║█████╗  ███████║██║     ██║   ███████║      █████╔╝███████╗ ███████╗
echo  ██╔══██║██╔══╝  ██╔══██║██║     ██║   ██╔══██║      ╚═══██╗██╔═══██╗╚════██║
echo  ██║  ██║███████╗██║  ██║███████╗██║   ██║  ██║     ██████╔╝╚██████╔╝███████║
echo  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝  ╚═╝     ╚═════╝  ╚═════╝ ╚══════╝
echo.
echo                  🚀 Allcare365 - Full Stack Server Launcher
echo ================================================================================

:: 啟動後端（Django）
echo [1/2] 啟動後端服務器...
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo ❌ 虛擬環境未找到！請先建立：python -m venv venv
    pause
    exit /b 1
)
echo ✅ 虛擬環境檢查完成
start "Backend Server" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python manage.py migrate && python manage.py runserver 8000"

:: 啟動前端（React）
echo.
echo [2/2] 啟動前端服務器...
cd /d "%~dp0frontend"
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js 未安裝或未加入 PATH！請安裝：https://nodejs.org/
    pause
    exit /b 1
)
if not exist "node_modules" (
    echo 📦 安裝前端依賴中...
    npm install
)
start "Frontend Server" cmd /k "cd /d %~dp0frontend && npm start"

echo.
echo ================================================================================ 
echo ✅ 前後端已啟動完成！
echo 💡 後端：http://localhost:8000
echo 💡 前端：http://localhost:3000
echo ================================================================================ 

pause
exit
