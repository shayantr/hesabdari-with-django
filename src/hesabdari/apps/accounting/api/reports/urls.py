from django.urls import path

from hesabdari.apps.accounting.api.reports.views import AccountReportDetails, account_report

urlpatterns = [
    path('accounts-report/', account_report, name='get_accounts_report'),
    path('accounts-report-detail/<int:pk>/', AccountReportDetails.as_view(), name='accounts_report_detail'),
]