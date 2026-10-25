from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    # Positive balance = we owe the supplier (accounts payable)
    balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00'),
        help_text='Outstanding payable to supplier (Rs.). Positive = we owe them.'
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    generic_name = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text='Salt / generic (e.g. Paracetamol) for alternate search'
    )
    category = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    expiry_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    barcode = models.ImageField(upload_to='barcodes/', blank=True)
    barcode_number = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text='Scannable barcode / EAN / internal code'
    )
    units_per_pack = models.PositiveIntegerField(
        default=1,
        help_text='Tablets/units in one pack (for loose sale). 1 = sold only as whole pack.'
    )
    allow_loose = models.BooleanField(
        default=True,
        help_text='Allow selling individual units from pack'
    )
    is_controlled = models.BooleanField(
        default=False,
        help_text='Controlled / narcotic — requires Rx on sale'
    )
    requires_rx = models.BooleanField(
        default=False,
        help_text='Prescription required at POS'
    )

    def is_expired(self):
        return timezone.now().date() > self.expiry_date

    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days

    @property
    def is_low_stock(self):
        return self.quantity < self.low_stock_threshold

    @property
    def status(self):
        if self.is_expired():
            return "Expired"
        elif self.days_until_expiry() <= 7:
            return "Expiring Soon"
        elif self.is_low_stock:
            return "Low Stock"
        return "Fresh"

    def __str__(self):
        return f"{self.name} ({self.status})"

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)
        if not self.barcode:
            EAN = barcode.get_barcode_class('ean13')
            ean = EAN(f'{self.id:012d}', writer=ImageWriter())
            buffer = BytesIO()
            ean.write(buffer)
            self.barcode.save(f'{self.id}.png', File(buffer), save=False)
        super().save(*args, **kwargs)

    
    def units_in_stock(self):
        """Stock always stored as base units (tablets/ml pieces)."""
        return int(self.quantity or 0)

    def packs_in_stock(self):
        upp = max(1, int(self.units_per_pack or 1))
        return self.units_in_stock() // upp

    def loose_remainder(self):
        upp = max(1, int(self.units_per_pack or 1))
        return self.units_in_stock() % upp

    def to_base_units(self, packs=0, loose_units=0):
        upp = max(1, int(self.units_per_pack or 1))
        return int(packs) * upp + int(loose_units)

    def display_stock(self):
        upp = max(1, int(self.units_per_pack or 1))
        if upp <= 1:
            return f"{self.quantity} units"
        p, r = divmod(int(self.quantity or 0), upp)
        if r:
            return f"{p} pack + {r} loose"
        return f"{p} pack"

    def total_batch_quantity(self):
        """Sum of non-expired active batch quantities."""
        today = timezone.now().date()
        return (
            self.batches.filter(is_active=True, expiry_date__gte=today)
            .aggregate(total=models.Sum('quantity'))['total'] or 0
        )

    def sync_quantity_from_batches(self):
        """Keep Product.quantity in sync with sum of active non-expired batches."""
        total = self.total_batch_quantity()
        if self.quantity != total:
            self.quantity = total
            self.save(update_fields=['quantity'])
        return total

    def allocate_fefo(self, qty_needed):
        """
        Allocate qty_needed from batches in FEFO order (earliest expiry first).
        Returns list of (batch, qty) without saving. Raises ValueError if insufficient.
        Caller must save inside a transaction with select_for_update.
        """
        qty_needed = int(qty_needed)
        if qty_needed <= 0:
            raise ValueError('Quantity must be positive.')
        today = timezone.now().date()
        batches = list(
            self.batches.select_for_update()
            .filter(is_active=True, quantity__gt=0, expiry_date__gte=today)
            .order_by('expiry_date', 'id')
        )
        remaining = qty_needed
        plan = []
        for b in batches:
            if remaining <= 0:
                break
            take = min(b.quantity, remaining)
            if take > 0:
                plan.append((b, take))
                remaining -= take
        if remaining > 0:
            available = qty_needed - remaining
            raise ValueError(
                f'Not enough sellable (non-expired) stock for {self.name}. '
                f'Requested {qty_needed}, available {available}.'
            )
        return plan




class ProductBatch(models.Model):
    """
    One physical batch/lot of a product.
    Sales use FEFO: earliest expiry_date first.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=64, help_text='Lot / batch number from supplier')
    quantity = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    purchase_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Cost per unit (Rs.) for this batch'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches'
    )
    received_date = models.DateField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['expiry_date', 'id']  # FEFO order
        verbose_name = 'Product Batch'
        verbose_name_plural = 'Product Batches'
        unique_together = [('product', 'batch_number')]

    def __str__(self):
        return f"{self.product.name} [{self.batch_number}] exp {self.expiry_date} qty {self.quantity}"

    @property
    def is_expired(self):
        return timezone.now().date() > self.expiry_date

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days


class SaleBatchAllocation(models.Model):
    """Tracks which batches were used for a sale (FEFO audit trail)."""
    sale = models.ForeignKey('Purchase', on_delete=models.CASCADE, related_name='batch_allocations')
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, related_name='sale_allocations')
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Sale#{self.sale_id} ← {self.quantity} from batch {self.batch.batch_number}"


class CustomerProfile(models.Model):
    """Pharmacy customer profile for credit (udhaar) tracking.
    balance > 0 means customer owes the pharmacy.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('5000.00'),
        help_text='Maximum allowed udhaar (Rs.)'
    )
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text='Current outstanding balance (Rs.). Positive = customer owes.'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'

    def __str__(self):
        return f"{self.user.username} — Rs.{self.balance}"

    @property
    def available_credit(self):
        return (self.credit_limit - self.balance).quantize(Decimal('0.01'))

    def can_take_credit(self, amount):
        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        return amount <= self.available_credit


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.get_or_create(user=instance)


class Purchase(models.Model):
    """Customer sale record (historically named Purchase).
    Tracks full/partial payment and credit (udhaar) portion.
    """
    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_CREDIT = 'credit'
    PAYMENT_SPLIT = 'split'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_CARD, 'Card / Bank'),
        (PAYMENT_CREDIT, 'Credit (Udhaar)'),
        (PAYMENT_SPLIT, 'Split (Partial + Credit)'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Amount received at time of sale (Rs.)'
    )
    amount_on_credit = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Amount added to customer udhaar (Rs.)'
    )
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_CASH
    )
    purchase_date = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)
    walk_in_name = models.CharField(max_length=120, blank=True)
    walk_in_phone = models.CharField(max_length=20, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bill_number = models.CharField(max_length=32, blank=True, db_index=True)
    rx_number = models.CharField(max_length=64, blank=True)
    rx_doctor = models.CharField(max_length=120, blank=True)
    rx_patient = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['-purchase_date']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'

    def __str__(self):
        return (
            f"Sale of {self.quantity} x {self.product.name} by "
            f"{self.customer.username} on {self.purchase_date.strftime('%Y-%m-%d %H:%M')}"
        )

    @property
    def is_fully_paid(self):
        return self.amount_on_credit <= 0


class CustomerPayment(models.Model):
    """Payment received against customer udhaar balance."""
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=10,
        choices=[('cash', 'Cash'), ('card', 'Card / Bank'), ('other', 'Other')],
        default='cash'
    )
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='received_payments'
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment Rs.{self.amount} from {self.customer.username} on {self.created_at.date()}"




class SupplierPurchase(models.Model):
    """
    Supplier invoice / goods received note (GRN).
    Increases stock via linked batches and increases supplier payable balance.
    """
    STATUS_DRAFT = 'draft'
    STATUS_RECEIVED = 'received'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_RECEIVED, 'Received'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchases')
    invoice_number = models.CharField(max_length=64, help_text='Supplier invoice / bill number')
    invoice_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_purchases'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-id']
        verbose_name = 'Supplier Purchase'
        verbose_name_plural = 'Supplier Purchases'
        unique_together = [('supplier', 'invoice_number')]

    def __str__(self):
        return f"{self.supplier.name} inv {self.invoice_number} — Rs.{self.total}"

    @property
    def amount_due(self):
        return (self.total - self.amount_paid).quantize(Decimal('0.01'))


class SupplierPurchaseLine(models.Model):
    """Line item on a supplier purchase; creates/updates a ProductBatch on receive."""
    purchase = models.ForeignKey(SupplierPurchase, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='supplier_lines')
    batch_number = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    expiry_date = models.DateField()
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    batch = models.ForeignKey(
        'ProductBatch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_lines'
    )

    def __str__(self):
        return f"{self.product.name} x{self.quantity} @ {self.unit_cost}"

    def save(self, *args, **kwargs):
        self.line_total = (Decimal(self.quantity) * Decimal(self.unit_cost)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class SupplierPayment(models.Model):
    """Payment made to a supplier against outstanding balance / invoices."""
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(
        max_length=12,
        choices=[('cash', 'Cash'), ('bank', 'Bank transfer'), ('cheque', 'Cheque'), ('other', 'Other')],
        default='cash'
    )
    reference = models.CharField(max_length=64, blank=True, help_text='Cheque no / txn id')
    purchase = models.ForeignKey(
        SupplierPurchase, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments', help_text='Optional: allocate to a specific invoice'
    )
    paid_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_payments_made'
    )
    notes = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at']

    def __str__(self):
        return f"Pay Rs.{self.amount} to {self.supplier.name} on {self.paid_at.date()}"


class Return(models.Model):
    """
    Customer return against a sale.
    On approval: restock (batch), reverse revenue via cash refund or credit to customer balance.
    """
    STATUS_PENDING = "Pending"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    REFUND_CASH = "cash"
    REFUND_CREDIT = "credit"
    REFUND_NONE = "none"
    REFUND_CHOICES = [
        (REFUND_CASH, "Cash refund"),
        (REFUND_CREDIT, "Credit to udhaar balance"),
        (REFUND_NONE, "No monetary refund"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="returns")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="returns")
    sale = models.ForeignKey(
        "Purchase", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="returns", help_text="Original sale this return refers to"
    )
    quantity = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    refund_method = models.CharField(max_length=10, choices=REFUND_CHOICES, default=REFUND_CASH)
    refund_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Monetary value refunded (Rs.)"
    )
    restock = models.BooleanField(default=True, help_text="Return units to inventory")
    date_requested = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processed_returns"
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date_requested"]

    def __str__(self):
        return f"Return of {self.quantity} x {self.product.name} by {self.customer.username} [{self.status}]"

    def suggested_refund(self):
        """Unit price from linked sale or current product price."""
        if self.sale_id and self.sale.quantity:
            unit = (self.sale.total_price / Decimal(self.sale.quantity)).quantize(Decimal("0.01"))
        else:
            unit = Decimal(self.product.price)
        return (unit * Decimal(self.quantity)).quantize(Decimal("0.01"))



class CashbookEntry(models.Model):
    """
    Real-time cash / bank book for every money movement.
    Positive amount = money in; negative = money out (stored as signed amount).
    """
    TYPE_SALE = 'sale'
    TYPE_SALE_RETURN = 'sale_return'
    TYPE_PURCHASE = 'purchase'
    TYPE_PURCHASE_RETURN = 'purchase_return'
    TYPE_CREDIT_GIVEN = 'credit_given'      # customer took udhaar (no cash in)
    TYPE_CREDIT_RECOVERY = 'credit_recovery'  # customer paid udhaar
    TYPE_SUPPLIER_PAYMENT = 'supplier_payment'
    TYPE_EXPENSE = 'expense'
    TYPE_INCOME_OTHER = 'income_other'
    TYPE_ADJUSTMENT = 'adjustment'
    TYPE_CHOICES = [
        (TYPE_SALE, 'Sale (cash/online in)'),
        (TYPE_SALE_RETURN, 'Sale return (cash out)'),
        (TYPE_PURCHASE, 'Supplier purchase (cash out)'),
        (TYPE_PURCHASE_RETURN, 'Purchase return (cash in)'),
        (TYPE_CREDIT_GIVEN, 'Credit given (udhaar)'),
        (TYPE_CREDIT_RECOVERY, 'Credit recovery'),
        (TYPE_SUPPLIER_PAYMENT, 'Supplier payment'),
        (TYPE_EXPENSE, 'Expense'),
        (TYPE_INCOME_OTHER, 'Other income'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
    ]

    EXPENSE_SALARY = 'salary'
    EXPENSE_UTILITY = 'utility'
    EXPENSE_TRAVEL = 'travel'
    EXPENSE_MAINTENANCE = 'maintenance'
    EXPENSE_RENT = 'rent'
    EXPENSE_MISC = 'misc'
    EXPENSE_CHOICES = [
        (EXPENSE_SALARY, 'Salary'),
        (EXPENSE_UTILITY, 'Utility bills'),
        (EXPENSE_TRAVEL, 'Traveling'),
        (EXPENSE_MAINTENANCE, 'Maintenance'),
        (EXPENSE_RENT, 'Rent'),
        (EXPENSE_MISC, 'Miscellaneous'),
    ]

    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    expense_category = models.CharField(
        max_length=20, choices=EXPENSE_CHOICES, blank=True, null=True
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text='Signed: positive = cash in, negative = cash out'
    )
    payment_channel = models.CharField(
        max_length=12,
        choices=[('cash', 'Cash'), ('online', 'Online'), ('bank', 'Bank'), ('other', 'Other')],
        default='cash'
    )
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=64, blank=True, help_text='Invoice / sale id')
    customer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashbook_entries'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashbook_entries'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashbook_created'
    )
    entry_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name = 'Cashbook Entry'
        verbose_name_plural = 'Cashbook Entries'

    def __str__(self):
        return f"{self.entry_type} {self.amount} on {self.entry_date}"

    @property
    def is_inflow(self):
        return self.amount >= 0


class MedicineMaster(models.Model):
    """
    National catalog for purchase autocomplete — NOT live stock.
    Stock is only created when goods are purchased into Product/ProductBatch.
    """
    product_name = models.CharField(max_length=255, db_index=True)
    brand_name = models.CharField(max_length=120, blank=True, db_index=True)
    ingredients = models.CharField(max_length=500, blank=True)
    company = models.CharField(max_length=200, blank=True)
    strength = models.CharField(max_length=120, blank=True)
    dosage_form = models.CharField(max_length=80, blank=True)
    pack_size = models.CharField(max_length=80, blank=True)
    therapeutic_group = models.CharField(max_length=120, blank=True)
    legacy_retail_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    legacy_trade_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_mrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['product_name']
        indexes = [
            models.Index(fields=['brand_name', 'product_name']),
        ]

    def __str__(self):
        return self.product_name


class AppNotification(models.Model):
    """In-app notification feed (expiry, credit due, sales summary)."""
    KIND_EXPIRY = 'expiry'
    KIND_CREDIT_DUE = 'credit_due'
    KIND_SALES = 'sales'
    KIND_STOCK = 'stock'
    KIND_SYSTEM = 'system'
    KIND_CHOICES = [
        (KIND_EXPIRY, 'Near / expired stock'),
        (KIND_CREDIT_DUE, 'Credit due'),
        (KIND_SALES, 'Sales summary'),
        (KIND_STOCK, 'Stock alert'),
        (KIND_SYSTEM, 'System'),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='app_notifications', help_text='Null = all staff'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.kind}] {self.title}"


class CreditDue(models.Model):
    """Tracks partial-payment / credit sale due dates for notifications."""
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_dues')
    sale = models.ForeignKey('Purchase', on_delete=models.SET_NULL, null=True, blank=True, related_name='dues')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    phone = models.CharField(max_length=20, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    is_settled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"{self.customer.username} due {self.amount} on {self.due_date}"



class StockAdjustment(models.Model):
    """Physical count / damage / expiry write-off."""
    REASON_COUNT = 'count'
    REASON_DAMAGE = 'damage'
    REASON_EXPIRY = 'expiry'
    REASON_OTHER = 'other'
    REASON_CHOICES = [
        (REASON_COUNT, 'Stock count difference'),
        (REASON_DAMAGE, 'Damage / breakage'),
        (REASON_EXPIRY, 'Expiry write-off'),
        (REASON_OTHER, 'Other'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='adjustments')
    batch = models.ForeignKey(
        'ProductBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='adjustments'
    )
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    quantity_delta = models.IntegerField(help_text='after - before (negative = stock out)')
    reason = models.CharField(max_length=12, choices=REASON_CHOICES, default=REASON_COUNT)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_adjustments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Adj {self.product_id} {self.quantity_delta} ({self.reason})'



class PosShift(models.Model):
    """Till / shift open-close for cash discipline."""
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [(STATUS_OPEN, 'Open'), (STATUS_CLOSED, 'Closed')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pos_shifts')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_float = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    closing_declared = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    variance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f'Shift {self.id} {self.user.username} ({self.status})'
