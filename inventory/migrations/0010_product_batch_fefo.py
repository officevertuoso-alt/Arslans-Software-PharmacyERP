# Phase 3 — Product batches + FEFO

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_customer_credit_phase2'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(help_text='Lot / batch number from supplier', max_length=64)),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('expiry_date', models.DateField()),
                ('purchase_cost', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Cost per unit (Rs.) for this batch', max_digits=10)),
                ('received_date', models.DateField(auto_now_add=True)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batches', to='inventory.product')),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='batches', to='inventory.supplier')),
            ],
            options={
                'verbose_name': 'Product Batch',
                'verbose_name_plural': 'Product Batches',
                'ordering': ['expiry_date', 'id'],
                'unique_together': {('product', 'batch_number')},
            },
        ),
        migrations.CreateModel(
            name='SaleBatchAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sale_allocations', to='inventory.productbatch')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batch_allocations', to='inventory.purchase')),
            ],
        ),
    ]
