from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicalreport',
            name='hash_value',
            field=models.CharField(max_length=128, null=True, blank=True),
        ),
        migrations.CreateModel(
            name='BlockchainRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_hash', models.CharField(max_length=128, db_index=True)),
                ('transaction_reference', models.CharField(max_length=256, null=True, blank=True)),
                ('block_timestamp', models.DateTimeField(null=True, blank=True)),
                ('verification_status', models.CharField(default='pending', max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blockchain_records', to='frontend.medicalreport')),
            ],
        ),
    ]
