@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title Arslan Pharmacy - Install
echo ============================================
echo  Arslan's Software Pharmacy ERP - INSTALL
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 3.11+ not found on PATH.
  echo Install from https://www.python.org/downloads/
  echo IMPORTANT: check "Add python.exe to PATH"
  pause
  exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo [ERROR] Need Python 3.10 or newer.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

set DJANGO_SETTINGS_MODULE=stocktime.settings
python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>nul

if not exist "backups" mkdir backups

echo.
echo [OK] Install complete.
echo Next: run windows\START.bat
echo Login: create superuser if needed:
echo   .venv\Scripts\python.exe manage.py createsuperuser
echo.
pause
