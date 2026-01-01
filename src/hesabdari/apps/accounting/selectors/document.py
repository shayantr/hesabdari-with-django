from hesabdari.apps.accounting.models import BalanceSheet


def get_document_balances_for_update(document, user):
    return BalanceSheet.objects.filter(document=document, user=user).select_related("account", "cheque__account").prefetch_related("cheque__balance_sheet")

def get_document_balances_for_change_status(id, user):
    return BalanceSheet.objects.filter(pk=id, user=user, is_active=True).select_related("cheque", "cheque__account")
