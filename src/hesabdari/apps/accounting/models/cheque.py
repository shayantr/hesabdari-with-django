from django.db import models
from django_jalali.db import models as jmodels
from hesabdari.apps.accounting.models.accounts import AccountsClass
from hesabdari.apps.users.models import User


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