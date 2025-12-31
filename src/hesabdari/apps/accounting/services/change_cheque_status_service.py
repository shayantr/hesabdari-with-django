from django.db import transaction

from hesabdari.apps.accounting.models import BalanceSheet, CashierCheque


class ChangeChequeStatusService:
    def __init__(self, balance,document, balance_cheque, update_cheque, all_new_balanceforms, all_new_chequeforms, user):
        self.balance = balance
        self.document = document
        self.balance_cheque = balance_cheque
        self.update_cheque = update_cheque
        self.all_new_balanceforms = all_new_balanceforms
        self.all_new_chequeforms = all_new_chequeforms
        self.user = user

    def execute(self):
        all_credit = 0
        all_debt = 0
        all_valid = True
        if not self.balance_cheque.is_valid() or not self.update_cheque.is_valid() or not self.document.is_valid():
            all_valid = False
            return False, 'لطفا فیلد های فرم خود را بازبینی کنید'
        all_debt, all_credit = self._update_totals(self.balance_cheque, all_debt, all_credit)
        for balance, cheque in zip(self.all_new_balanceforms, self.all_new_chequeforms):
            if not balance.is_valid() or not cheque.is_valid():
                all_valid = False
                return False, 'لطفا فیلد های فرم خود را بازبینی کنید'
        for balance in self.all_new_balanceforms:
            all_debt, all_credit = self._update_totals(balance, all_debt, all_credit)
        if all_credit != all_debt:
            return False, 'مجموع بدهکاری و بستانکاری برابر نیست.'
        with transaction.atomic():
            d = self.document.save()
            self.balance.is_active = False
            self.balance.save()
            ex_balance = self.balance_cheque.save(commit=False)
            chnaged_cheque = self.update_cheque.save()
            ex_balance.document = d
            ex_balance.cheque = chnaged_cheque
            ex_balance.save()
            self._save_new_forms(d)
        if all_valid:
            return True, 'فرم با موفقیت ثبت شد'



    def _save_new_forms(self, document):
        cheques_to_create = []
        balances_to_create = []
        for balance, cheque in zip(self.all_new_balanceforms, self.all_new_chequeforms):
            b = balance.save(commit=False)
            b.user = self.user
            if cheque.cleaned_data.get('name'):
                c = cheque.save(commit=False)
                c.user = self.user
                cheques_to_create.append(c)
                # c.save()
                b.cheque = c
            b.document = document
            balances_to_create.append(b)
            # b.save()
        CashierCheque.objects.bulk_create(cheques_to_create)
        BalanceSheet.objects.bulk_create(balances_to_create)




    def _update_totals(self, form, all_debt, all_credit):
        if form.cleaned_data.get('transaction_type') == "debt":
            all_debt += form.cleaned_data.get('amount') or 0
        elif form.cleaned_data.get('transaction_type') == "credit":
            all_credit += form.cleaned_data.get('amount') or 0
        return all_debt, all_credit