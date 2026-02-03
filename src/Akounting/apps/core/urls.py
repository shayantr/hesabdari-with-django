from django.urls import path

from Akounting.apps.core.views import backup_list_view

urlpatterns = [
    path('backups/', backup_list_view, name='backup_list'),
]