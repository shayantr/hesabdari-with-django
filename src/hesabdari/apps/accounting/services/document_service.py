from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse


def validate_balance(all_balanceforms):
    all_credit = all_debt = 0
    for balance in all_balanceforms:
        if balance.cleaned_data.get('transaction_type') == "debt":
            all_debt += balance.cleaned_data.get('amount') or 0
        elif balance.cleaned_data.get('transaction_type') == "credit":
            all_credit += balance.cleaned_data.get('amount') or 0

    if all_credit != all_debt:
        raise ValidationError("مجموع بدهکاری و بستانکاری برابر نیست")

@transaction.atomic
def save_document(document_instance, all_balanceforms, all_chequeforms, user):
    d = document_instance.save(commit=False)
    for balance, cheque in zip(all_balanceforms, all_chequeforms):
        b = balance.save(commit=False)
        if cheque.cleaned_data.get('name'):
            c = cheque.save()
            b.cheque = c
        b.document = d
        b.save()
    return d
