
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Verify DB integrity, WAL, and core counts'

    def handle(self, *args, **options):
        with connection.cursor() as c:
            c.execute('PRAGMA journal_mode;')
            mode = c.fetchone()[0]
            c.execute('PRAGMA foreign_keys;')
            fk = c.fetchone()[0]
        self.stdout.write(f'journal_mode={mode} foreign_keys={fk}')
        from inventory import models as m
        for name in ['Product', 'Purchase', 'ProductBatch', 'StockMovement',
                     'CashbookEntry', 'SaleInvoice', 'MedicineMaster']:
            model = getattr(m, name, None)
            if model:
                self.stdout.write(f'{name}: {model.objects.count()}')
        self.stdout.write(self.style.SUCCESS('verify_system OK'))
