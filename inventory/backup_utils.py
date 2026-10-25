
"""Local SQLite backup / restore helpers."""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings


def backup_dir() -> Path:
    d = Path(settings.BASE_DIR) / 'backups'
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return Path(settings.DATABASES['default']['NAME'])


def create_backup(label: str = 'manual') -> Path:
    src = db_path()
    if not src.exists():
        raise FileNotFoundError(f'Database not found: {src}')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = backup_dir() / f'db_{stamp}_{label}.sqlite3'
    shutil.copy2(src, dest)
    return dest


def list_backups():
    files = sorted(backup_dir().glob('db_*.sqlite3'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def restore_backup(filename: str) -> Path:
    safe = Path(filename).name
    src = backup_dir() / safe
    if not src.exists() or not safe.startswith('db_') or not safe.endswith('.sqlite3'):
        raise FileNotFoundError('Invalid backup file')
    dest = db_path()
    # safety copy before restore
    create_backup(label='pre_restore')
    shutil.copy2(src, dest)
    return dest


def prune_backups(keep: int = 14):
    files = list_backups()
    for f in files[keep:]:
        try:
            f.unlink()
        except OSError:
            pass


def maybe_auto_backup():
    """Run if interval elapsed. Returns path or None."""
    from django.utils import timezone
    from inventory.models import AppSettings

    cfg = AppSettings.get()
    if not cfg.backup_enabled:
        return None
    now = timezone.now()
    if cfg.last_auto_backup_at:
        hours = (now - cfg.last_auto_backup_at).total_seconds() / 3600.0
        if hours < (cfg.backup_interval_hours or 24):
            return None
    path = create_backup(label='auto')
    cfg.last_auto_backup_at = now
    cfg.save(update_fields=['last_auto_backup_at'])
    prune_backups(cfg.backup_keep_count or 14)
    return path
