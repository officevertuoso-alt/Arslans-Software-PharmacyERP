from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0012_return_accounting'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashbookEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_type', models.CharField(choices=[('sale', 'Sale (cash/online in)'), ('sale_return', 'Sale return (cash out)'), ('purchase', 'Supplier purchase (cash out)'), ('purchase_return', 'Purchase return (cash in)'), ('credit_given', 'Credit given (udhaar)'), ('credit_recovery', 'Credit recovery'), ('supplier_payment', 'Supplier payment'), ('expense', 'Expense'), ('income_other', 'Other income'), ('adjustment', 'Adjustment')], max_length=20)),
                ('expense_category', models.CharField(blank=True, choices=[('salary', 'Salary'), ('utility', 'Utility bills'), ('travel', 'Traveling'), ('maintenance', 'Maintenance'), ('rent', 'Rent'), ('misc', 'Miscellaneous')], max_length=20, null=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Signed: positive = cash in, negative = cash out', max_digits=14)),
                ('payment_channel', models.CharField(choices=[('cash', 'Cash'), ('online', 'Online'), ('bank', 'Bank'), ('other', 'Other')], default='cash', max_length=12)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('reference', models.CharField(blank=True, help_text='Invoice / sale id', max_length=64)),
                ('entry_date', models.DateField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cashbook_created', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cashbook_entries', to=settings.AUTH_USER_MODEL)),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cashbook_entries', to='inventory.supplier')),
            ],
            options={'ordering': ['-entry_date', '-id'], 'verbose_name': 'Cashbook Entry', 'verbose_name_plural': 'Cashbook Entries'},
        ),
        migrations.CreateModel(
            name='MedicineMaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(db_index=True, max_length=255)),
                ('brand_name', models.CharField(blank=True, db_index=True, max_length=120)),
                ('ingredients', models.CharField(blank=True, max_length=500)),
                ('company', models.CharField(blank=True, max_length=200)),
                ('strength', models.CharField(blank=True, max_length=120)),
                ('dosage_form', models.CharField(blank=True, max_length=80)),
                ('pack_size', models.CharField(blank=True, max_length=80)),
                ('therapeutic_group', models.CharField(blank=True, max_length=120)),
                ('legacy_retail_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('legacy_trade_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('current_mrp', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['product_name']},
        ),
        migrations.CreateModel(
            name='AppNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('expiry', 'Near / expired stock'), ('credit_due', 'Credit due'), ('sales', 'Sales summary'), ('stock', 'Stock alert'), ('system', 'System')], max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('link', models.CharField(blank=True, max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, help_text='Null = all staff', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='app_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CreditDue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('due_date', models.DateField()),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('is_settled', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credit_dues', to=settings.AUTH_USER_MODEL)),
                ('sale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dues', to='inventory.purchase')),
            ],
            options={'ordering': ['due_date']},
        ),
        migrations.AddIndex(
            model_name='medicinemaster',
            index=models.Index(fields=['brand_name', 'product_name'], name='inventory_m_brand_n_idx'),
        ),
    ]
