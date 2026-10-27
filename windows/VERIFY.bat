@echo off
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python manage.py check
python -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','stocktime.settings'); django.setup(); from django.db import connection; c=connection.cursor(); c.execute('PRAGMA journal_mode'); print('journal_mode=', c.fetchone()); from inventory.models import Product,Purchase,StockMovement; print('products',Product.objects.count()); print('sales',Purchase.objects.count()); print('movements',StockMovement.objects.count())"
pause
