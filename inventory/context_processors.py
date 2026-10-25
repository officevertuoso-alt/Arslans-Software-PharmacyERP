
def app_ui(request):
    theme = request.session.get('ui_theme')
    shop = "Arslan's Software Pharmacy"
    try:
        from inventory.models import AppSettings
        from inventory.backup_utils import maybe_auto_backup
        cfg = AppSettings.get()
        if not theme:
            theme = cfg.theme
        shop = cfg.shop_name
        # lightweight auto-backup check (once per request is ok for local)
        try:
            maybe_auto_backup()
        except Exception:
            pass
    except Exception:
        theme = theme or 'pharmacy'
    return {
        'ui_theme': theme or 'pharmacy',
        'shop_name': shop,
    }
