from django.db import transaction

from hesabdari.apps.accounting.forms import BalanceSheetForm, CashierChequeForm
from hesabdari.apps.accounting.utils.combined_forms import PostCombinedForm


class UpdateDocumentService:
    def __init__(self, document, balance_sheets, document_form, new_balance_forms, new_cheque_forms, deleted_ids, user, post_data, files):
        self.document = document
        self.balance_sheets = balance_sheets
        self.document_form = document_form
        self.new_balance_forms = new_balance_forms
        self.new_cheque_forms = new_cheque_forms
        self.deleted_ids = deleted_ids
        self.user = user
        self.post_data = post_data
        self.files = files

    def execute(self):
        combined_forms = []
        deleted_balances = []
        all_credit, all_debt, all_valid = 0, 0, True
        for balance in self.balance_sheets:
            if not balance.is_active:
                if balance.transaction_type == "debt":
                    all_debt += balance.amount or 0
                elif balance.transaction_type == "credit":
                    all_credit += balance.amount or 0
                continue

            if balance.id in self.deleted_ids:
                deleted_balances.append(balance)
                continue
            balance_form = BalanceSheetForm(
                self.post_data, self.files, prefix=f"{balance.id}-update-balance", instance=balance
            )
            cheque_form = CashierChequeForm(
                self.post_data or None, prefix=f"{balance.id}-update-cheque", instance=balance.cheque
            )
            if not balance_form.is_valid():
                return False, None
            if not cheque_form.is_valid():
                return False, None

            combined_forms.append(PostCombinedForm(balance.id, balance_form, cheque_form))
            all_debt, all_credit = self._update_totals(balance_form, all_debt, all_credit)

        all_valid = (
            # all(item.form_balance.is_valid() for item in combined_forms) and
            # all(item.form_cheque.is_valid() for item in combined_forms) and
            all(ncf.is_valid() for ncf in self.new_cheque_forms)
        )
        if not self.document_form.is_valid():
            all_valid = False
        for nbf in self.new_balance_forms:
            if not nbf.is_valid():
                # balance_errors[i] = bal.errors
                return False, nbf.errors
        for item in self.new_balance_forms:
            all_debt, all_credit = self._update_totals(item, all_debt, all_credit)
        if all_debt != all_credit:
            return False, 'مجموع بدهکاری و بستانکاری برابر نیست.'

        if not all_valid:
            return False, "اطلاعات فرم چک شود"
        try:
            with transaction.atomic():
                self._handle_delete(deleted_balances)
                self.document_form.save()
                self._save_existing(combined_forms)
                self._save_new()
        except Exception:
            return False, "خطا در ذخیره اطلاعات"

        return True, None
    def _update_totals(self, form, debt, credit):
        amount = form.cleaned_data.get("amount") or 0
        if form.cleaned_data.get("transaction_type") == "debt":
            debt += amount
        else:
            credit += amount
        return debt, credit

    def _handle_delete(self, balances):
        for balance in balances:
            balance.delete()
            if balance.cheque:
                last_inactive = balance.cheque.balance_sheet.filter(is_active=False).last()
                if last_inactive:
                    last_inactive.is_active = True
                    last_inactive.save()
                else:
                    balance.cheque.delete()


    def _save_existing(self, combined_forms):
        for item in combined_forms:
            balance = item.form_balance.save(commit=False)
            if item.form_cheque.cleaned_data.get('name'):
                cheque = item.form_cheque.save(commit=False)
                cheque.user = self.user
                if cheque.cheque_type is None:
                    if balance.transaction_type == 'debt':
                        cheque.cheque_type = 'دریافتنی'
                    elif balance.transaction_type == 'credit':
                        cheque.cheque_type = 'پرداختنی'
                cheque.save()
                balance.cheque = cheque
            balance.document = self.document
            balance.save()

    def _save_new(self):
        for bal_form, cheque_form in zip(self.new_balance_forms, self.new_cheque_forms):
            balance = bal_form.save(commit=False)
            balance.user = self.user
            if cheque_form.cleaned_data.get('name'):
                cheque = cheque_form.save(commit=False)
                cheque.user = self.user
                cheque.save()
                balance.cheque = cheque
            balance.document = self.document
            balance.save()