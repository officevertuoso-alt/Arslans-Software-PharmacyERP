@echo off
cd /d "%~dp0"
if not exist "windows\START.bat" (
  echo Missing windows\START.bat
  pause
  exit /b 1
)
call windows\START.bat
