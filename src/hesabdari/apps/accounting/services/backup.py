import sqlite3
import subprocess, os, zipfile
from django.conf import settings
from datetime import datetime

from django.db import connection


def backup_full_system():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = f'backup_full_{ts}'
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    sqlite_backup_path = os.path.join(backup_dir, f'{base}.sqlite3')
    zip_path = os.path.join(backup_dir, f'{base}.zip')
    src_conn = connection.connection
    dst_conn = sqlite3.connect(sqlite_backup_path)

    with dst_conn:
        src_conn.backup(dst_conn)

    dst_conn.close()

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(sqlite_backup_path, arcname='database.sqlite3')

        for root, _, files in os.walk(settings.MEDIA_ROOT):
            for f in files:
                p = os.path.join(root, f)
                z.write(
                    p,
                    arcname=f'media/{os.path.relpath(p, settings.MEDIA_ROOT)}'
                )

    return zip_path
