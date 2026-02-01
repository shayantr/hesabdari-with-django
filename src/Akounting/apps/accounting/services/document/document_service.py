from django.db import transaction, DatabaseError

class DocumentService:
    def __init__(self, document_form, balance_forms, cheque_forms):
        self.document_form = document_form
        self.balance_forms = balance_forms
        self.cheque_forms = cheque_forms

    def execute(self):
        if not self.document_form.is_valid():
            return False, self.document_form.errors
        for balance, cheque in zip(self.balance_forms, self.cheque_forms):
            if not balance.is_valid() or not cheque.is_valid():
                return False, {
                    "type": "row",
                    "form": balance,
                    'err_id': balance.prefix
                }

        total_debt = total_credit = 0

        for balance in self.balance_forms:
            t = balance.cleaned_data.get("transaction_type")
            amount = balance.cleaned_data.get("amount") or 0
            if t == "debt":
                total_debt += amount
            elif t == "credit":
                total_credit += amount
        if total_debt != total_credit:
            return False, "مجموع بدهکاری و بستانکاری برابر نیست!"

        try:
            with transaction.atomic():
                document = self.document_form.save()
                for balance, cheque in zip(self.balance_forms, self.cheque_forms):
                    b = balance.save(commit=False)
                    if cheque.cleaned_data.get("name"):
                        c = cheque.save()
                        b.cheque = c

                    b.document = document
                    b.save()
        except DatabaseError:
            return False, "مشکلی در ذخیره اطلاعات پیش آمده است"

        return True, document