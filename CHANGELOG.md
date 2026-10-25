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
