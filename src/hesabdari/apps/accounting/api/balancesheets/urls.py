from django.urls import path

from hesabdari.apps.accounting.api.balancesheets.views import BalanceListView, filter_balance, csv_balance

urlpatterns = [
    path('balance-lists/', BalanceListView.as_view(), name='balance_lists'),
    path('balance-lists/filter-balance/', filter_balance, name='filter_balance'),
    path('export-csv-balance/', csv_balance, name='csv_balance'),
]