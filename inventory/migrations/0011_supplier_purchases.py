# Phase 4 — Supplier purchases, lines, payments, supplier balance

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0010_product_batch_fefo'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Outstanding payable to supplier (Rs.). Positive = we owe them.', max_digits=14),
        ),
        migrations.AddField(
            model_name='supplier',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='supplier',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='supplier',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='supplier',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='address',
            field=models.TextField(blank=True),
        ),
        migrations.AlterModelOptions(
            name='supplier',
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='SupplierPurchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(help_text='Supplier invoice / bill number', max_length=64)),
                ('invoice_date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('received', 'Received'), ('cancelled', 'Cancelled')], default='received', max_length=12)),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('tax', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supplier_purchases', to=settings.AUTH_USER_MODEL)),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchases', to='inventory.supplier')),
            ],
            options={
                'verbose_name': 'Supplier Purchase',
                'verbose_name_plural': 'Supplier Purchases',
                'ordering': ['-invoice_date', '-id'],
                'unique_together': {('supplier', 'invoice_number')},
            },
        ),
        migrations.CreateModel(
            name='SupplierPurchaseLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(max_length=64)),
                ('quantity', models.PositiveIntegerField()),
                ('unit_cost', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('expiry_date', models.DateField()),
                ('line_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchase_lines', to='inventory.productbatch')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='supplier_lines', to='inventory.product')),
                ('purchase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='inventory.supplierpurchase')),
            ],
        ),
        migrations.CreateModel(
            name='SupplierPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('bank', 'Bank transfer'), ('cheque', 'Cheque'), ('other', 'Other')], default='cash', max_length=12)),
                ('reference', models.CharField(blank=True, help_text='Cheque no / txn id', max_length=64)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('paid_at', models.DateTimeField(auto_now_add=True)),
                ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supplier_payments_made', to=settings.AUTH_USER_MODEL)),
                ('purchase', models.ForeignKey(blank=True, help_text='Optional: allocate to a specific invoice', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='inventory.supplierpurchase')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='inventory.supplier')),
            ],
            options={
                'ordering': ['-paid_at'],
            },
        ),
    ]
