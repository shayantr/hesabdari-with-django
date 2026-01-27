from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from hesabdari.apps.users.models import User



class AccountsClass(MPTTModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='users', blank=True)
    name = models.CharField(max_length=255)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        db_table = 'accounts'

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        # Get all ancestors (excluding self) in order from root to parent
        ancestors = self.get_ancestors()

        # Collect ucode values from ancestors and self
        name_list = [ancestor.name for ancestor in ancestors if ancestor.name]  # Filter out None values
        if self.name:
            name_list.append(self.name)
        name_list = " > ".join(name_list) if name_list else "خالی"

        return f"{name_list}"
