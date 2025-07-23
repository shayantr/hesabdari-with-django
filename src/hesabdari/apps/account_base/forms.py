from django import forms
from treebeard.forms import MoveNodeForm

from hesabdari.apps.account_base.models import AccountsClass, BalanceSheet, CashierCheque, Document


class AccountsForm(MoveNodeForm):
    class Meta:
        model = AccountsClass
        fields = ['name']


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
            'maturityـamount': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'مبلغ', 'id': "floatingInput"}),
            'account': forms.Select(attrs={'class': 'dropdown form-select form-select-lg' }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'توضیحات', "cols":20, "rows":1}),
            'image': forms.FileInput(attrs={'class': 'form-control','accept': 'image/jpeg,application/pdf', 'placeholder': 'بارگزاری عکس'}),
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
