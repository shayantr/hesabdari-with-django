from django import forms
from treebeard.forms import MoveNodeForm

from hesabdari.apps.account_base.models import AccountsClass, BalanceSheet, CashierCheque, Document


class AccountsForm(forms.ModelForm):
    class Meta:
        model = AccountsClass
        fields = '__all__'


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = "__all__"
        widgets={
            'user': forms.HiddenInput(),
            'date_created': forms.TextInput(
            attrs={'class': 'form-control', 'data-jdp': 'data-jdp', 'placeholder': 'تاریخ ثبت'}),
        }


class BalanceSheetForm(forms.ModelForm):
    class Meta:
        model = BalanceSheet
        exclude = ['is_active']
        widgets = {
            'user': forms.HiddenInput(),
            'amount': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'مبلغ', 'id': "floatingInput"}),
            'account': forms.Select(attrs={'class': 'dropdown form-select form-select-lg ', 'style': 'display:none;' }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'توضیحات', "cols":10, "rows":1}),
            'image': forms.FileInput(attrs={'class': 'form-control','accept': 'image/jpeg,application/pdf', 'placeholder': 'بارگزاری عکس'}),
            'transaction_type': forms.HiddenInput(),
            'document': forms.HiddenInput(),
            'cheque': forms.HiddenInput(),
            'date_created': forms.TextInput(
                attrs={'class': 'form-control', 'data-jdp':'data-jdp', 'placeholder':'تاریخ ثبت'}),
        }
        labels = {
            'cash_only': 'مبلغ نقدی',
        }
        error_messages = {
            'amount': {
                "required": 'poresh kon'
            }
        }


class CashierChequeForm(forms.ModelForm):
    class Meta:
        model = CashierCheque
        fields = '__all__'
        widgets = {
            'user': forms.HiddenInput(),
            'account': forms.Select(attrs={'class': 'dropdown form-select form-select-lg ', 'style': 'display:none;'}),

            'maturity_date': forms.TextInput(
                attrs={'class': 'form-control', 'data-jdp':'data-jdp', 'placeholder':'زمان سررسید'}),
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'نام', 'id': "floatingInput"}),
            'Cheque_numbder': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'شماره چک', 'id': "floatingInput"}),
            'cheque_status': forms.Select(attrs={'class': 'dropdown form-select form-select-lg'}),
            'cheque_type': forms.HiddenInput(),

        }
