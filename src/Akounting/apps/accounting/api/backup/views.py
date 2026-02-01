import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, FileResponse, HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from Akounting.apps.accounting.services.backup import backup_full_system

import os, zipfile, shutil
from datetime import datetime
from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS


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
            "backup:download_backup",
            args=[os.path.basename(path)]
        ),
        'filename': os.path.basename(path)
    })

def restore_full_system_from_zip(zip_path):
    db_path = settings.DATABASES['default']['NAME']
    base_dir = settings.BASE_DIR

    archive_dir = os.path.join(base_dir, 'archived_dbs')
    os.makedirs(archive_dir, exist_ok=True)

    # 1. بستن اتصال دیتابیس
    connections[DEFAULT_DB_ALIAS].close()

    # 2. آرشیو دیتابیس فعلی
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    archived_db = os.path.join(
        archive_dir,
        f'db_{ts}.sqlite3'
    )
    shutil.copy(db_path, archived_db)

    # 3. استخراج بکاپ
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extract('database.sqlite3', base_dir)
        z.extractall(base_dir, members=[
            m for m in z.namelist() if m.startswith('media/')
        ])

    # 4. جایگزینی دیتابیس
    os.rename(
        os.path.join(base_dir, 'database.sqlite3'),
        db_path
    )

    return archived_db

@login_required
@require_POST
def full_restore_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    file = request.FILES.get('backup')
    if not file:
        return JsonResponse({'error': 'فایل ارسال نشده'}, status=400)

    temp_path = os.path.join(settings.BASE_DIR, 'tmp_restore.zip')
    with open(temp_path, 'wb+') as f:
        for chunk in file.chunks():
            f.write(chunk)

    archived = restore_full_system_from_zip(temp_path)

    return JsonResponse({
        'success': True,
        'archived_db': os.path.basename(archived),
        'message': 'ریستور انجام شد. لطفاً سیستم را ری‌استارت کنید.'
    })