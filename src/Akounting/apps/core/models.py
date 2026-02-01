from django.db import models

# Create your models here.

class SystemState(models.Model):
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(blank=True, null=True)
    reason = models.CharField(blank=True, max_length=255)

    class Meta:
        db_table = 'system_state'

    def __str__(self):
        return "locked" if self.is_locked else "unlocked"

class SystemBackupState(models.Model):
    last_backup_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'system_backup_state'

