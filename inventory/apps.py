
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        try:
            from django.db import connection
            if connection.vendor == 'sqlite':
                with connection.cursor() as c:
                    c.execute('PRAGMA journal_mode=WAL;')
                    c.execute('PRAGMA synchronous=NORMAL;')
                    c.execute('PRAGMA temp_store=MEMORY;')
                    c.execute('PRAGMA mmap_size=268435456;')
                    c.execute('PRAGMA cache_size=-64000;')
                    c.execute('PRAGMA foreign_keys=ON;')
        except Exception:
            pass
