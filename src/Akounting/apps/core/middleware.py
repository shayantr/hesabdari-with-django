from django.shortcuts import render
from django.utils.timezone import now

from Akounting.apps.accounting.api.backup.views import backup_system_view
from Akounting.apps.core.models import SystemState, SystemBackupState


class SystemLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        state = SystemState.objects.first()

        if state and state.is_locked:
            # اجازه فقط به superuser
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)

            return render(request, 'system_locked.html', status=503)

        return self.get_response(request)

class DailyBackupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        today = now().date()
        state, _ = SystemBackupState.objects.get_or_create(id=1)

        if state.last_backup_date != today:
            backup_system_view(request)
            state.last_backup_date = today
            state.save()

        return self.get_response(request)