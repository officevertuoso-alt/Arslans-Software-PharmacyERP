# Changelog — Arslan's Software Pharmacy ERP

## [Phase 1] — 2026-10-26 — Commercial Foundation

### Security & Configuration
- `SECRET_KEY` and `DEBUG` now read from environment variables (`.env` supported via python-dotenv).
- `ALLOWED_HOSTS` configurable via env.
- Added `LocaleMiddleware` and bilingual language list (English + اردو) ready for Phase 7.

### Pakistan localization
- `TIME_ZONE` changed from `Asia/Manila` to **`Asia/Karachi`**.
- Currency symbol standardized to **`Rs.`** (PKR).
- Checkout and success messages no longer show ₱.

### Money safety (critical)
- Checkout and payment handling now use **`Decimal`** with 2-decimal quantize instead of `float`.
- Income report totals also use Decimal.

### Transaction safety (critical)
- Sale (checkout) now runs inside **`transaction.atomic()`** + `select_for_update()` to prevent overselling under concurrent use.
- Return approval also uses atomic + row lock; already-processed returns are rejected.

### Other
- Added `requirements.txt`.
- Added `custom_404` / `custom_500` handlers so settings no longer point to missing views.
- Expired products blocked at purchase time.

### Still pending (next phases)
- Batch / lot / FEFO stock model
- Proper supplier purchase / goods-receipt ledger
- Customer credit (udhaar) & partial payments
- Full bilingual UI + reports
- Backup / restore module
- Automated tests & Windows installer

## [Phase 2] — 2026-10-26 — Customer Credit (Udhaar)

### Models
- `CustomerProfile` — phone, address, credit_limit, balance (positive = owes pharmacy)
- Auto-create profile on new User
- `Purchase` (Sale) extended: `amount_paid`, `amount_on_credit`, `payment_method`, `notes`
- `CustomerPayment` — payments against outstanding balance

### Checkout
- Full cash, full credit, or split (partial + udhaar)
- Credit limited by `credit_limit - balance`
- Atomic: stock + sale + balance update together

### Staff tools
- `/customers/ledger/` — all customer balances
- `/customers/ledger/<id>/` — detail + receive payment

### Customer
- `/my-ledger/` — own sales, payments, and outstanding balance

### Migration
- `0009_customer_credit_phase2.py`


## [Phase 3] — 2026-10-26 — Batches + FEFO

### Models
- `ProductBatch` — batch_number, quantity, expiry, purchase_cost, supplier, FEFO ordering
- `SaleBatchAllocation` — which batches were used on each sale
- `Product.allocate_fefo()` / `sync_quantity_from_batches()` helpers

### Sales
- Checkout deducts stock from earliest-expiring non-expired batches first (FEFO)
- Falls back to legacy `Product.quantity` when no batches exist yet
- Allocations stored for audit

### Receiving
- `/batches/receive/` — goods receipt with lot number, expiry, cost
- `/batches/` and `/batches/product/<id>/` — batch list with expiry highlighting

### Migration
- `0010_product_batch_fefo.py`


## [Phase 4] — 2026-10-26 — Supplier Purchases & Payables

### Models
- `Supplier.balance` — accounts payable (positive = we owe supplier)
- `SupplierPurchase` — invoice/GRN with subtotal, tax, total, amount_paid
- `SupplierPurchaseLine` — product, batch, qty, unit_cost, expiry → creates ProductBatch
- `SupplierPayment` — payments to suppliers, optional invoice allocation

### Workflow
1. **New purchase** `/supplier-purchases/add/` — multi-line invoice
2. On receive: batches created/updated (FEFO-ready), stock synced, supplier balance += unpaid
3. **Pay supplier** `/suppliers/<id>/pay/` — reduce balance, optional invoice allocation
4. List `/supplier-purchases/` and detail views

### Migration
- `0011_supplier_purchases.py`


## [Phase 5] — 2026-10-26 — Returns Accounting

### Return model
- Link to original `sale` (Purchase)
- `refund_method`: cash / credit to udhaar / none
- `refund_amount`, `restock`, `processed_at`, `processed_by`

### Approval workflow
- Suggested refund from original sale unit price (or product price)
- Restock into existing non-expired batch or create `RET-...` batch
- Credit refund reduces customer outstanding balance
- Cash refund recorded on the return (drawer handled operationally)
- Full atomic transaction

### UI
- Manage returns: approve form with amount, method, restock checkbox

### Migration
- `0012_return_accounting.py`


## [Phase 6] — 2026-10-26 — Reports & Backup/Restore

### Reports dashboard (`/reports/`)
- Sales today (cash vs credit), 7-day revenue
- Estimated COGS and gross profit from batch costs
- Stock valuation (sell price + cost)
- Customer receivables and supplier payables
- Low/expiring/expired counts

### Daily closing (`/reports/daily-closing/`)
- Per-day sales, cash in, new udhaar, collections, supplier payments, refunds, net cash

### Backup / Restore
- `/backup/` — SQLite online backup download
- `/restore/` — upload backup with automatic safety copy + integrity check
- Files stored under `backups/` (gitignored)

No new DB migration required for Phase 6.


## [Phase 7] — 2026-10-26 — Bilingual Urdu + English

### i18n
- Language switcher in navbar (English / اردو)
- Django `set_language` via `/i18n/`
- `locale/ur/LC_MESSAGES/django.po` + compiled `.mo`
- Base navigation and key labels use `{% trans %}`

### Branding
- Navbar title: **Arslan's Software**

### Note
If you add more strings, run on a machine with gettext:
`django-admin makemessages -l ur` then `django-admin compilemessages`


## [Phase 8] — 2026-10-26 — Cashbook, Charts, Master catalog, Notifications

### Cashbook (`/cashbook/`)
- Real-time ledger: sale, purchase, credit, returns, **expenses** (salary, utility, travel, maintenance, rent, misc)
- Tabs: All / Cash In / Cash Out / Expenses
- Manual expense entry form

### Charts (`/charts/`) — LalanaChami-style
- Sales per Month (bar)
- Sales per Drug top 10 (horizontal bar)
- Cashbook net 14-day line
- Chart.js (no Mongo embed dependency)

### Medicine master
- Catalog only (not stock)
- Bulk import CSV/XLSX, export CSV
- Autocomplete API `/medicine-master/suggest/`

### Notifications
- In-app feed + browser desktop Notification API
- Near expiry, expired stock, credit due, daily sales summary
- `/notifications/refresh/` to regenerate alerts

### Migration
- `0013_cashbook_master_notifications.py`


## [Phase 8B] — 2026-10-26 — POS credit/partial, due dates, suggestions

### Checkout
- Payment methods: Cash, Online, Credit, Partial
- Paid < total → phone + due date required; `CreditDue` saved
- Cash + paid 0 → confirm switch to Credit
- Previous bakaya shown; link to credit profile
- Customer name autocomplete (`/api/customer-suggest/`)

### Credit recovery
- Receiving payment settles oldest `CreditDue` rows
- Cashbook `credit_recovery` entry

### Loose sale
- Optional "Loose / unit sale" flag on shop forms (session)

### Purchase
- Tip link to Medicine Master for catalog-driven SKU setup


## [Phase 8C] — 2026-10-26 — Fast POS (Candela-style)

### Screen `/pos/`
- Always-focused barcode / name search
- Multi-item cart in session
- Scanner: code + Enter adds line (qty merges)
- Keyboard: F2 search, Enter add, ↑↓ cart, +/- qty, Del remove, F12 pay
- Payment: Cash / Online / Credit / Partial + due phone fields
- Atomic multi-line FEFO sale + cashbook + CreditDue


## [Phase 9] — 2026-10-26 — Receipt, Hold, Discount, Barcode, Stock Adj

### POS
- **F9 Hold bill** / recall list
- **Bill discount** distributed across lines
- **Walk-in name** on bill
- **Bill number** `BYYYYMMDD####`
- After pay → **printable receipt** (80mm CSS + auto print)
- Scan by **barcode_number** field

### Product
- `barcode_number`, `units_per_pack`, `allow_loose`

### Stock
- `/stock-adjust/` count / damage / expiry write-off (FEFO on reduce)

### Migration
- `0014_pos_advanced.py`


## [Phase 10] — 2026-10-26 — Pack/Loose + Generic alternates

### Product
- `generic_name` (salt) for search & alternates
- Stock in **base units**; `units_per_pack` converts pack ↔ loose
- `display_stock()` e.g. `2 pack + 3 loose`

### POS
- **Loose / unit** vs **Full pack** sale mode
- Search by name, generic, barcode
- **F4** alternates (same generic, in-stock)
- Unit price = pack price / units_per_pack for loose lines

### Migration
- `0015_generic_pack.py`


## [Phase 11] — 2026-10-26 — Controlled drugs + Shift/Till

### Controlled / Rx
- Product: `is_controlled`, `requires_rx`
- POS: if cart has such items → Rx number + doctor required
- Saved on each sale line: `rx_number`, `rx_doctor`, `rx_patient`

### Shift / Till
- `/shift/open/` — opening float
- POS blocked until shift open
- `/shift/close/` — expected cash (float + cash sales + recoveries) vs counted, variance

### Migration
- `0016_controlled_shift.py`


## [Phase 12] — 2026-10-26 — Candela-style F1 Product Help + Medicine preload

### POS
- **F1 Product Help** modal: searchable grid (Stock + Master catalog)
- Columns: type, name, generic/salt, brand, price, stock
- Keyboard: ↑↓ Enter in help grid
- Master row → create Product SKU qty=0 (stock via purchase)

### Catalog preload
- `python manage.py preload_medicines [xlsx]`
- UI: `/medicine-master/preload/`
- Imports Pakistan Medicine Master List (~41k) into MedicineMaster
- **Not stock** — Candela-style preloaded drug list for search


## [Phase 13] — 2026-10-26 — Remaining commercial features

### Customers & invoices
- `CustomerParty` walk-in/credit customers
- `SaleInvoice` multi-line bill header linked from POS
- Invoice list + **same-day void** (restock + audit + cashbook adjustment)

### Supplier returns
- FEFO stock out, supplier balance down, cashbook purchase_return

### Purchasing
- Auto draft PO from low-stock products

### Compliance & finance
- Controlled / Rx sales register
- Simple P&L (revenue − batch COGS − expenses)
- Audit log

### Migration
- `0017_phase13_complete.py`

### Still not full Candela
- FBR live API, multi-branch godown, SMS gateway, native offline installer


## [Phase 14] — 2026-10-26 — SMS / WhatsApp gateway

- `inventory/messaging.py`: console | http | twilio
- MessageLog, `/messaging/` test + due reminders
- POS optional send bill SMS/WhatsApp
- `.env.example` messaging keys


## [Phase 15] — 2026-10-26 — Backup scheduler, restore, reset, themes, GUI

- Local SQLite backup to `backups/` + auto schedule (interval hours)
- Restore with pre-restore safety copy
- Factory reset (superuser) for transactional data
- Themes: light / dark / pharmacy green
- Context processor + modern navbar/cards CSS
- `/system/` tools page


## [Phase 16] — 2026-10-27 — Windows standalone + speed + stock sync

- `windows/INSTALL.bat` `START.bat` `STOP.bat` `BACKUP_NOW.bat` `VERIFY.bat`
- Waitress 8-thread local server (lag-free vs runserver)
- SQLite WAL + cache PRAGMAs on app ready
- `StockMovement` ledger + `/stock-movements/`
- System health check
- Root `START_PHARMACY.bat` / `INSTALL_PHARMACY.bat`
