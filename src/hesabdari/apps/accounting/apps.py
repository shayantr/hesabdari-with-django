from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hesabdari.apps.accounting'
    label = 'accounting'

    def ready(self):
        from . import signals
