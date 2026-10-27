@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title Arslan Pharmacy ERP
echo Starting Arslan's Software Pharmacy...

if not exist ".venv\Scripts\python.exe" (
  echo Run windows\INSTALL.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
set DJANGO_SETTINGS_MODULE=stocktime.settings
set PYTHONUNBUFFERED=1
set MESSAGING_ENABLED=%MESSAGING_ENABLED%

REM Auto-migrate (safe, fast)
python manage.py migrate --noinput

REM Open browser after short delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000/"

echo.
echo Server: http://127.0.0.1:8000/
echo Press Ctrl+C to stop.
echo.

REM Waitress = production-ish multi-thread WSGI (faster than runserver)
python -c "from waitress import serve; from stocktime.wsgi import application; print('Waitress on 127.0.0.1:8000'); serve(application, host='127.0.0.1', port=8000, threads=8, channel_timeout=120)"

if errorlevel 1 (
  echo Waitress failed - falling back to runserver...
  python manage.py runserver 127.0.0.1:8000
)
pause
