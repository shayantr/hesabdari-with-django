from django.urls import path, include
from rest_framework.routers import DefaultRouter

from hesabdari.apps.accounting.views.account import AccountsView, create_accounts, edit_account, delete_account, \
    UpdateBulkAccount, accouns_manager
from hesabdari.apps.accounting.views.backup import backup_system_view, download_backup
from hesabdari.apps.accounting.views.balance import BalanceListView, filter_balance, csv_balance
from hesabdari.apps.accounting.views.calendar import calendar_page, all_events, cheques_of_day
from hesabdari.apps.accounting.views.cheque import deletechequeview, ChequeListView, filter_receivable_cheques, \
    filter_payable_cheques, csv_cheque
from hesabdari.apps.accounting.views.document import createbalancesheet, GetFormFragmentView, UpdateBalanceView, \
    delete_document, ChangeStatusCheque
from hesabdari.apps.accounting.views.reports import account_report, AccountReportDetails

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
    path('transfer-accounts/', UpdateBulkAccount.as_view(), name='transfer-accounts'),
    path('export-csv-cheque/', csv_cheque, name='csv_cheque'),
    path('export-csv-balance/', csv_balance, name='csv_balance'),
    path('full_backup/', backup_system_view, name='full_backup'),
    path('download-backup/<str:filename>/', download_backup, name='download_backup'),
    path('accounts-manager/', accouns_manager, name='accounts_manager'),
    path('events/', calendar_page, name='calendar_page'),
    path('events-list/', all_events, name='events_list'),
    path('cheque-day/', cheques_of_day, name='cheque_day'),

]