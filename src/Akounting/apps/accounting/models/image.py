from django.db import models

from Akounting.apps.accounting.utils.custom_path import user_directory_file_path
from Akounting.apps.users.models import User


class Image(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='image_user')
    file = models.ImageField(upload_to=user_directory_file_path)
    class Meta:
        db_table = 'image'

