from django.urls import path

from Akounting.apps.accounting.api.backup.views import download_backup, backup_system_view, full_restore_view

app_name = 'backup'


urlpatterns = [
    path('full_backup/', backup_system_view, name='full_backup'),
    path('download-backup/<str:filename>/', download_backup, name='download_backup'),
    path('full_restore/', full_restore_view, name='restore_backup'),
]