from django import forms
from treebeard.forms import MoveNodeForm

from hesabdari.apps.account_base.models import AccountsClass, BalanceSheet, CashierCheque, Document


class AccountsForm(MoveNodeForm):
    class Meta:
        model = AccountsClass
        fields = ['name']

    # def save(self, commit=True, parent=None):
    #     """ این متد برای تعیین والد دسته‌بندی در ذخیره‌سازی فرم است. """
    #     instance = super().save(commit=False)  # هنوز در دیتابیس ذخیره نمی‌شود
    #     if parent:
    #         instance.insert_at(parent, save=commit)  # اضافه کردن به والد
    #     elif commit:
    #         instance.save()
    #     return instance


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'

class BalanceSheetForm(forms.ModelForm):
    class Meta:
        model = BalanceSheet
        fields = '__all__'
        widgets = {
            'user': forms.HiddenInput(),
            'maturityـamount': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'مبلغ نقدی', 'id': "floatingInput"}),
            'account': forms.Select(attrs={'class': 'dropdown form-select form-select-lg' }),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control','accept': 'image/jpeg,application/pdf'}),
            'transaction_type': forms.HiddenInput(),
            'document': forms.HiddenInput(),
            'cheque': forms.HiddenInput(),
        }
        labels = {
            'cash_only': 'مبلغ نقدی',
        }


class CashierChequeForm(forms.ModelForm):
    class Meta:
        model = CashierCheque
        fields = '__all__'
        widgets = {
            'user': forms.HiddenInput(),
            'maturity_date': forms.TextInput(
                attrs={'class': 'form-control', 'data-jdp':'data-jdp', 'placeholder':'زمان سررسید'}),
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'نام', 'id': "floatingInput"}),
            'Cheque_numbder': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'شماره چک', 'id': "floatingInput"}),
            'cheque_status': forms.Select(attrs={'class': 'dropdown form-select form-select-lg'}),

        }
