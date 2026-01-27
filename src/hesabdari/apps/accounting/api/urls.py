from django.urls import path, include

from hesabdari.apps import accounting



urlpatterns = [
    path('', include('hesabdari.apps.accounting.api.documents.urls')),
    path('', include('hesabdari.apps.accounting.api.balancesheets.urls')),
    path('', include('hesabdari.apps.accounting.api.cheques.urls')),
    path('', include('hesabdari.apps.accounting.api.accounts.urls')),
    path('', include('hesabdari.apps.accounting.api.reports.urls')),
    path('', include('hesabdari.apps.accounting.api.calendar.urls')),

]