
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0014_pos_advanced'),
    ]
    operations = [
        migrations.AddField(
            model_name='product',
            name='generic_name',
            field=models.CharField(blank=True, db_index=True, help_text='Salt / generic (e.g. Paracetamol) for alternate search', max_length=200),
        ),
    ]
