
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('inventory', '0018_message_log')]
    operations = [
        migrations.CreateModel(
            name='AppSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('theme', models.CharField(choices=[('light', 'Light'), ('dark', 'Dark'), ('pharmacy', 'Pharmacy green')], default='pharmacy', max_length=20)),
                ('backup_enabled', models.BooleanField(default=True)),
                ('backup_interval_hours', models.PositiveIntegerField(default=24)),
                ('backup_keep_count', models.PositiveIntegerField(default=14)),
                ('last_auto_backup_at', models.DateTimeField(blank=True, null=True)),
                ('shop_name', models.CharField(default="Arslan's Software Pharmacy", max_length=120)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
