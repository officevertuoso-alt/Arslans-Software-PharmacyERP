@echo off
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','stocktime.settings'); django.setup(); from inventory.backup_utils import create_backup; p=create_backup('manual'); print('Backup:', p)"
pause
