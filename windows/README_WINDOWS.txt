
================================================================================
 Arslan's Software Pharmacy ERP — Windows Standalone / Portable Guide
================================================================================

REQUIREMENT (one-time on the PC):
  Python 3.10+ from python.org with "Add to PATH" checked.
  No need to install Django globally — INSTALL.bat creates a private .venv.

QUICK START
  1) Copy whole project folder to D:\ArslansPharmacy (or any path)
  2) Double-click  windows\INSTALL.bat   (once)
  3) Double-click  windows\CREATE_ADMIN.bat   (once — make login user)
  4) Double-click  windows\START.bat   (daily)
  5) Browser opens http://127.0.0.1:8000/

DAILY USE
  START.bat  — runs Waitress (8 threads), auto-migrate, opens browser
  STOP.bat   — kills port 8000
  BACKUP_NOW.bat — instant SQLite copy to backups\

SPEED / LAG-FREE
  - SQLite WAL mode + 64MB cache + mmap
  - Waitress multi-thread (not Django runserver)
  - Local only 127.0.0.1 (no internet required to sell)
  - LocMem cache for sessions

TRANSACTIONS / STOCK SYNC
  - Sales/purchases/returns use database atomic transactions
  - StockMovement ledger records quantity changes
  - Menu: More → Stock movements / System health

BACKUP SCHEDULE
  - App → System tools: enable auto backup interval
  - Also use BACKUP_NOW.bat before major changes

TRUE "NO PYTHON INSTALL" OPTION
  Advanced: use Windows embeddable Python package from python.org,
  extract beside project, point INSTALL to that python.exe.
  Official embeddable zip does not include pip by default — use
  standard Python installer for reliability.

FBR / SMS
  Optional; configure .env (see .env.example)

================================================================================
