from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        # Defer SQLite PRAGMAs until first DB connection (not during app init checks)
        from django.db.backends.signals import connection_created

        def _sqlite_optimize(sender, connection, **kwargs):
            if connection.vendor != 'sqlite':
                return
            try:
                with connection.cursor() as c:
                    c.execute('PRAGMA journal_mode=WAL;')
                    c.execute('PRAGMA synchronous=NORMAL;')
                    c.execute('PRAGMA temp_store=MEMORY;')
                    c.execute('PRAGMA mmap_size=268435456;')
                    c.execute('PRAGMA cache_size=-64000;')
                    c.execute('PRAGMA foreign_keys=ON;')
            except Exception:
                pass

        connection_created.connect(_sqlite_optimize, dispatch_uid='inventory_sqlite_optimize')
