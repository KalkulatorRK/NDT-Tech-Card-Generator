from django.apps import AppConfig


class StandardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.standards"
    verbose_name = "Нормативные документы"

    def ready(self):
        """Wire up signals; actual DB population happens via setup_initial_data command."""
        pass
