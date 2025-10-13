from django.urls import path, include
from rest_framework.routers import DefaultRouter

from hesabdari.apps.account_base.views import createbalancesheet, \
    GetFormFragmentView, AccountsView, UpdateBalanceView, deletechequeview, ChequeListView, filter_payable_cheques, \
    edit_account, delete_account, BalanceListView, \
    filter_balance, create_accounts, account_report, AccountReportDetails, delete_document, \
    ChangeStatusCheque, filter_receivable_cheques, csv_cheque

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='documents')



urlpatterns = [
    path('create-document/', createbalancesheet, name='create-document'),
    path('items/get-form/', GetFormFragmentView.as_view(), name='get_form_fragment'),
    path('items/accounts-list/', AccountsView.as_view(), name='get_accounts_list'),
    path('accounts-report/', account_report, name='get_accounts_report'),
    path('accounts-report-detail/<int:pk>/', AccountReportDetails.as_view(), name='accounts_report_detail'),
    path('items/accounts-list/create', create_accounts, name='create_accounts'),
    path('update/<int:pk>/', UpdateBalanceView.as_view(), name='UpdateBalanceView'),
    path('delete-cheque/', deletechequeview, name='delete-cheque-view'),
    path('cheque-lists/', ChequeListView.as_view(), name='cheque-lists-view'),
    path('cheque-lists/filter-receivable/', filter_receivable_cheques, name='filter_receivable_cheques'),
    path('cheque-lists/filter-credits/', filter_payable_cheques, name='filter_payable_cheques'),
    path('accounts/edit/<int:pk>/', edit_account, name='edit_account'),
    path('accounts/delete/<int:pk>/', delete_account, name='delete_account'),
    path('balance-lists/', BalanceListView.as_view(), name='balance_lists'),
    path('balance-lists/filter-balance/', filter_balance, name='filter_balance'),
    # path('delete-balance/', delete_balance, name='delete_balance'),
    path('delete-document/<int:pk>/', delete_document, name='delete_document'),
    path('change-cheque-status/<int:pk>/', ChangeStatusCheque.as_view(), name='change_status_cheque'),
    path('export-csv-cheque/', csv_cheque, name='csv_cheque'),
]