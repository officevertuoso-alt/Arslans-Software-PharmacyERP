# Phase 5 — Return accounting fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0011_supplier_purchases'),
    ]

    operations = [
        migrations.AddField(
            model_name='return',
            name='notes',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='return',
            name='processed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='return',
            name='processed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_returns', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='return',
            name='refund_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Monetary value refunded (Rs.)', max_digits=12),
        ),
        migrations.AddField(
            model_name='return',
            name='refund_method',
            field=models.CharField(choices=[('cash', 'Cash refund'), ('credit', 'Credit to udhaar balance'), ('none', 'No monetary refund')], default='cash', max_length=10),
        ),
        migrations.AddField(
            model_name='return',
            name='restock',
            field=models.BooleanField(default=True, help_text='Return units to inventory'),
        ),
        migrations.AddField(
            model_name='return',
            name='sale',
            field=models.ForeignKey(blank=True, help_text='Original sale this return refers to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='returns', to='inventory.purchase'),
        ),
        migrations.AlterField(
            model_name='return',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='returns', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='return',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='returns', to='inventory.product'),
        ),
        migrations.AlterModelOptions(
            name='return',
            options={'ordering': ['-date_requested']},
        ),
    ]
