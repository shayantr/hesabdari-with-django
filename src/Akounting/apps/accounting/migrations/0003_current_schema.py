import Akounting.apps.accounting.utils.custom_path
import django.db.models.deletion
import django.utils.timezone
import django_jalali.db.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.ImageField(upload_to=Akounting.apps.accounting.utils.custom_path.user_directory_file_path)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='image_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'image',
            },
        ),
        migrations.AlterField(
            model_name='balancesheet',
            name='image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounting.image'),
        ),
        migrations.AlterField(
            model_name='document',
            name='date_created',
            field=django_jalali.db.models.jDateField(default=django.utils.timezone.now),
        ),
    ]
