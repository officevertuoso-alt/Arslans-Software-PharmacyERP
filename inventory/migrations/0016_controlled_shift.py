
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0015_generic_pack'),
    ]
    operations = [
        migrations.AddField(model_name='product', name='is_controlled', field=models.BooleanField(default=False, help_text='Controlled / narcotic — requires Rx on sale')),
        migrations.AddField(model_name='product', name='requires_rx', field=models.BooleanField(default=False, help_text='Prescription required at POS')),
        migrations.AddField(model_name='purchase', name='rx_number', field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name='purchase', name='rx_doctor', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='purchase', name='rx_patient', field=models.CharField(blank=True, max_length=120)),
        migrations.CreateModel(
            name='PosShift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('opened_at', models.DateTimeField(auto_now_add=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('opening_float', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('closing_declared', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('expected_cash', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('variance', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=10)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pos_shifts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-opened_at']},
        ),
    ]
