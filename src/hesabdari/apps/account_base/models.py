from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from treebeard.mp_tree import MP_Node


# Create your models here.

class Accounts(MPTTModel):
    name = models.CharField(max_length=50, unique=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class MPTTMeta:
        order_insertion_by = ['name']
