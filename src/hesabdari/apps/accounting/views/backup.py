import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, FileResponse, HttpResponseForbidden, JsonResponse
from django.urls import reverse

from hesabdari.apps.accounting.services.backup import backup_full_system


@login_required
def download_backup(request, filename):
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    file_path = os.path.join(backup_dir, filename)

    if not os.path.exists(file_path):
        raise Http404()

    if not request.user.is_superuser:
        raise Http404()

    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename
    )

@login_required
def backup_system_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    path = backup_full_system()
    return JsonResponse({
        'success': True,
        'download_url': reverse(
            "download_backup",
            args=[os.path.basename(path)]
        ),
        'filename': os.path.basename(path)
    })