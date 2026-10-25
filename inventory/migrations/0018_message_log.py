
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0017_phase13_complete'),
    ]
    operations = [
        migrations.CreateModel(
            name='MessageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp')], max_length=12)),
                ('to_phone', models.CharField(max_length=20)),
                ('body', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=12)),
                ('provider', models.CharField(blank=True, max_length=32)),
                ('provider_response', models.TextField(blank=True)),
                ('purpose', models.CharField(blank=True, max_length=64)),
                ('related_bill', models.CharField(blank=True, max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
