# Generated by Django 5.1.6 on 2025-06-07 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account_base', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashiercheque',
            name='cheque_status',
            field=models.CharField(choices=[('جاری', 'Current'), ('وصولی', 'Collection'), ('برگشتنی', 'Bounced'), ('عودتی', 'Return Ch'), ('امانی', 'Escrow')], default='جاری', max_length=255),
        ),
    ]
