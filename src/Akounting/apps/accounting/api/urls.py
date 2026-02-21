from django.urls import path, include

from Akounting.apps import accounting



urlpatterns = [
    path('', include('Akounting.apps.accounting.api.documents.urls')),
    path('', include('Akounting.apps.accounting.api.balancesheets.urls')),
    path('', include('Akounting.apps.accounting.api.cheques.urls')),
    path('', include('Akounting.apps.accounting.api.accounts.urls')),
    path('', include('Akounting.apps.accounting.api.reports.urls')),
    path('', include('Akounting.apps.accounting.api.calendar.urls')),
    path('', include('Akounting.apps.accounting.api.backup.urls')),
    path('', include('Akounting.apps.accounting.api.image_gallery.urls')),

]