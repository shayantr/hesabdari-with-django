from django.apps import AppConfig


class AccountBaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hesabdari.apps.account_base'

    def ready(self):
        from . import signals
