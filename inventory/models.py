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
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField()

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
