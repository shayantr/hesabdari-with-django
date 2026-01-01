from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from treebeard.mp_tree import MP_Node
from django_jalali.db import models as jmodels
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

class BalanceSheetQuerySet(models.QuerySet):
    def for_account_with_children(self, account):
        """
        filter records base on parent and child
        """
        return self.filter(
            account__tree_id=account.tree_id,
            account__lft__gte=account.lft,
            account__rght__lte=account.rght
        )

class BalanceSheetManager(models.Manager):
    def get_queryset(self):
        return BalanceSheetQuerySet(self.model, using=self._db)

    def for_account_with_children(self, account):
        return self.get_queryset().for_account_with_children(account)

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
    previous_cheque_status = models.CharField(max_length=50, null=True, blank=True)
    objects = jmodels.jManager()
    with_children = BalanceSheetManager()

    class Meta:
        db_table = 'balance_sheet'




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
    in_cash = models.CharField(max_length=255, null=True, blank=True)
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
    objects = jmodels.jManager()

    class Meta:
        db_table = 'cashier_cheque'