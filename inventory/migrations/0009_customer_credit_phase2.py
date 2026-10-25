# Generated manually for Phase 2 — Customer credit / udhaar

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0008_product_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('address', models.TextField(blank=True)),
                ('credit_limit', models.DecimalField(decimal_places=2, default=Decimal('5000.00'), help_text='Maximum allowed udhaar (Rs.)', max_digits=12)),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Current outstanding balance (Rs.). Positive = customer owes.', max_digits=12)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Customer Profile',
                'verbose_name_plural': 'Customer Profiles',
            },
        ),
        migrations.CreateModel(
            name='CustomerPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('card', 'Card / Bank'), ('other', 'Other')], default='cash', max_length=10)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credit_payments', to=settings.AUTH_USER_MODEL)),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='purchase',
            name='amount_on_credit',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Amount added to customer udhaar (Rs.)', max_digits=10),
        ),
        migrations.AddField(
            model_name='purchase',
            name='amount_paid',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Amount received at time of sale (Rs.)', max_digits=10),
        ),
        migrations.AddField(
            model_name='purchase',
            name='notes',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='purchase',
            name='payment_method',
            field=models.CharField(choices=[('cash', 'Cash'), ('card', 'Card / Bank'), ('credit', 'Credit (Udhaar)'), ('split', 'Split (Partial + Credit)')], default='cash', max_length=10),
        ),
        migrations.AlterModelOptions(
            name='purchase',
            options={'ordering': ['-purchase_date'], 'verbose_name': 'Sale', 'verbose_name_plural': 'Sales'},
        ),
    ]
