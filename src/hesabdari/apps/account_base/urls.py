from django.urls import path, include

from hesabdari.apps.account_base.views import createbalancesheet, \
    GetFormFragmentView, AccountsView, CreateAccounts, UpdateBalanceView, deletechequeview, ChequeListView, \
    filter_debit_cheques, filter_credit_cheques, edit_account, delete_account, BalanceListView, filter_credit_balance, \
    filter_debit_balance

urlpatterns = [
    path('create-document/', createbalancesheet, name='create-document'),
    path('items/get-form/', GetFormFragmentView.as_view(), name='get_form_fragment'),
    path('items/accounts-list/', AccountsView.as_view(), name='get_accounts_list'),
    path('items/accounts-list/create', CreateAccounts.as_view(), name='create_accounts'),
    path('update/<int:pk>/', UpdateBalanceView.as_view(), name='UpdateBalanceView'),
    path('delete-cheque/', deletechequeview, name='delete-cheque-view'),
    path('cheque-lists/', ChequeListView.as_view(), name='cheque-lists-view'),
    path('cheque-lists/filter-debits/', filter_debit_cheques, name='filter_debit_cheques'),
    path('cheque-lists/filter-credits/', filter_credit_cheques, name='filter_credit_cheques'),
    path('accounts/edit/<int:pk>/', edit_account, name='edit_account'),
    path('accounts/delete/<int:pk>/', delete_account, name='delete_account'),
    path('balance-lists/', BalanceListView.as_view(), name='balance_lists'),
    path('balance-lists/filter-balance-credits/', filter_credit_balance, name='filter_credit_balance'),
    path('balance-lists/filter-balance-debits/', filter_debit_balance, name='filter_debit_balance'),
]