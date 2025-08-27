from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from treebeard.mp_tree import MP_Node
from django_jalali.db import models as jmodels
from hesabdari.apps.accounts.models import User

class AccountsClass(MPTTModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts', blank=True)
    name = models.CharField(max_length=255)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

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




class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    date_created = jmodels.jDateField(default=jmodels.timezone.now())

    def delete(self, *args, **kwargs):
        if self.items.filter(is_active=False).exists():
            raise ValueError("به دلیل وجود تراکنش غیر فعال، امکان حذف این سند وجود ندارد.")
        super().delete(*args, **kwargs)


class BalanceSheet(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('debt', 'بدهی'),
        ('credit', 'بستانکاری'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='balancesheet')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='items', blank=True, null=True)
    date_created = jmodels.jDateField(auto_now_add=True, editable=True)
    account = models.ForeignKey(AccountsClass, on_delete=models.CASCADE, related_name='balance_sheets', blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    cheque = models.ForeignKey('CashierCheque', on_delete=models.SET_NULL, null=True, blank=True, related_name='balance_sheet')
    amount = models.IntegerField( verbose_name='مبلغ')
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)



class CashierCheque(models.Model):
    class ChequeType(models.TextChoices):
        CURRENT = 'جاری', 'جاری'
        COLLECTION = 'وصولی', 'وصولی'
        BOUNCED = 'برگشتنی', 'برگشتنی'
        RETURN_CH = 'عودتی', 'عودتی'
        ESCROW = 'امانی', 'امانی'
    class ChequeTypeChoices(models.TextChoices):
        payable = 'پرداختنی', 'پرداختنی'
        receivable = 'دریافتنی', 'دریافتنی'
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cashiercheque', blank=True, null=True)
    account = models.ForeignKey(AccountsClass, on_delete=models.CASCADE, related_name='Bank_cheque', null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    Cheque_numbder = models.IntegerField(null=True, blank=True)
    created_at = jmodels.jDateField(auto_now_add=True, editable=True)
    maturity_date = jmodels.jDateField(verbose_name='زمان سررسید', null=True, blank=True)
    cheque_status = models.CharField(
        max_length=255,
        choices=ChequeType.choices,
        default=ChequeType.CURRENT,
    )
    cheque_type = models.CharField(
        max_length=255,
        choices=ChequeTypeChoices.choices,
        blank=True,
        null=True,)
