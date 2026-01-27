from django.db import models

from hesabdari.apps.accounting.models.accounts import AccountsClass
from hesabdari.apps.accounting.models.document import Document
from hesabdari.apps.users.models import User
from django_jalali.db import models as jmodels



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