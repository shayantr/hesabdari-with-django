from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from twisted.python.failure import count

from hesabdari.apps.accounting.models.balancesheet import BalanceSheet


# @receiver(pre_save, sender=BalanceSheet)
# def save_previous_cheque_status(sender, instance, **kwargs):
#     print('main')
#     if instance.cheque:
#         previous_cheque = CashierCheque.objects.filter(pk=instance.cheque.pk).first()
#         if instance.pk:
#             instance_balance = BalanceSheet.objects.filter(cheque=previous_cheque, is_active=False).last()
#             if instance_balance and instance_balance.cheque and instance_balance.cheque.cheque_status != instance.cheque.cheque_status:
#                 instance.previous_cheque_status = instance_balance.cheque.cheque_status
#                 print(1)
#
#         else:
#             instance_balance = BalanceSheet.objects.filter(cheque=previous_cheque, is_active=False).last()
#             instance.previous_cheque_status = instance_balance.cheque.cheque_status
#             print(2)

@receiver(post_delete, sender=BalanceSheet)
def restore_cheque_status_on_delete(sender, instance, **kwargs):
    if instance.cheque and instance.cheque.cheque_status:
        if instance.previous_cheque_status:
            cheque = instance.cheque
            cheque.cheque_status = instance.previous_cheque_status
            cheque.save()