from django.db import models
from django_jalali.db import models as jmodels
from hesabdari.apps.users.models import User


class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    date_created = jmodels.jDateField(default=jmodels.timezone.now())
    objects = jmodels.jManager()

    class Meta:
        db_table = 'document'

    def delete(self, *args, **kwargs):
        for bs in self.items.all():
            if bs.is_active is False:
                raise ValueError("به دلیل وجود تراکنش غیر فعال، امکان حذف این سند وجود ندارد.")
            else:
                bs.delete()
        super().delete(*args, **kwargs)