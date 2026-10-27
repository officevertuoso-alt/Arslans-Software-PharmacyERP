
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0019_app_settings'),
    ]
    operations = [
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('move_type', models.CharField(choices=[
                    ('sale', 'Sale'), ('sale_void', 'Sale void restock'),
                    ('purchase', 'Purchase / receive'), ('return_in', 'Customer return'),
                    ('return_out', 'Supplier return'), ('adjust', 'Adjustment'),
                    ('supplier_return', 'Supplier return'), ('opening', 'Opening'),
                ], max_length=20)),
                ('quantity_delta', models.IntegerField(help_text='+in / -out')),
                ('quantity_after', models.IntegerField(default=0)),
                ('reference', models.CharField(blank=True, db_index=True, max_length=64)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movements', to='inventory.productbatch')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movements', to='inventory.product')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddIndex(
            model_name='stockmovement',
            index=models.Index(fields=['product', '-created_at'], name='inventory_s_product_idx'),
        ),
        migrations.AddIndex(
            model_name='stockmovement',
            index=models.Index(fields=['move_type', '-created_at'], name='inventory_s_move_ty_idx'),
        ),
    ]
