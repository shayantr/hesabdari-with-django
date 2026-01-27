from django.urls import path

from hesabdari.apps.accounting.api.cheques.views import deletechequeview, ChequeListView, filter_receivable_cheques, \
    filter_payable_cheques, csv_cheque, ChangeStatusCheque

urlpatterns = [
    path('delete-cheque/', deletechequeview, name='delete-cheque-view'),
    path('cheque-lists/', ChequeListView.as_view(), name='cheque-lists-view'),
    path('cheque-lists/filter-receivable/', filter_receivable_cheques, name='filter_receivable_cheques'),
    path('cheque-lists/filter-credits/', filter_payable_cheques, name='filter_payable_cheques'),
    path('export-csv-cheque/', csv_cheque, name='csv_cheque'),
    path('change-cheque-status/<int:pk>/', ChangeStatusCheque.as_view(), name='change_status_cheque'),

]