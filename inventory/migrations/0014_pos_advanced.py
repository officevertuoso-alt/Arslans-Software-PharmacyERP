from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0013_cashbook_master_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='barcode_number',
            field=models.CharField(blank=True, db_index=True, help_text='Scannable barcode / EAN / internal code', max_length=64),
        ),
        migrations.AddField(
            model_name='product',
            name='units_per_pack',
            field=models.PositiveIntegerField(default=1, help_text='Tablets/units in one pack (for loose sale). 1 = sold only as whole pack.'),
        ),
        migrations.AddField(
            model_name='product',
            name='allow_loose',
            field=models.BooleanField(default=True, help_text='Allow selling individual units from pack'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='walk_in_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='purchase',
            name='walk_in_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='purchase',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='purchase',
            name='bill_number',
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.CreateModel(
            name='StockAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_before', models.IntegerField()),
                ('quantity_after', models.IntegerField()),
                ('quantity_delta', models.IntegerField(help_text='after - before (negative = stock out)')),
                ('reason', models.CharField(choices=[('count', 'Stock count difference'), ('damage', 'Damage / breakage'), ('expiry', 'Expiry write-off'), ('other', 'Other')], default='count', max_length=12)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='adjustments', to='inventory.productbatch')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_adjustments', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='inventory.product')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
