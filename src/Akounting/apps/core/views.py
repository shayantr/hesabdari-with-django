import os
from datetime import datetime
from pathlib import Path

import jalali_date
import jdatetime
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone


# Create your views here.
@staff_member_required
def backup_list_view(request):
    backup_dir = Path(settings.BASE_DIR) / "backups"

    backups = []
    if backup_dir.exists():
        files = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and f.suffix == ".zip"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        for f in files:
            x= timezone.make_aware(datetime.fromtimestamp(f.stat().st_mtime))
            backups.append({
                "name": f.name,
                "path": f,
                "modified_at": jalali_date.date2jalali(timezone.make_aware(
                    datetime.fromtimestamp(f.stat().st_mtime))
                ),
                "size": f.stat().st_size
            })

    return render(request, "core/backup_list.html", {
        "backups": backups
    })
