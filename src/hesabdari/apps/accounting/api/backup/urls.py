from django.urls import path

from hesabdari.apps.accounting.api.backup.views import download_backup, backup_system_view

urlpatterns = [
    path('full_backup/', backup_system_view, name='full_backup'),
    path('download-backup/<str:filename>/', download_backup, name='download_backup'),
]