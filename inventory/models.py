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
    category = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    expiry_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    barcode = models.ImageField(upload_to='barcodes/', blank=True)

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
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Pending"
    )
    date_requested = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return of {self.quantity} x {self.product.name} by {self.customer.username}"
