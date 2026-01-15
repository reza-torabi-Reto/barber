from django.apps import AppConfig


class SalonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.salon'

    def ready(self):
        import apps.salon.signals
