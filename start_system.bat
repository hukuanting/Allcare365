@echo off
echo Starting Backend...
start "Backend" cmd /v:on /k "set PYTHONIOENCODING=utf-8 && venv\Scripts\activate && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm start"

echo System startup initiated.
pause
