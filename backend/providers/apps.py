from django.apps import AppConfig


class ProvidersConfig(AppConfig):
    """Configuration for the providers app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'providers'
    verbose_name = 'Service Providers'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import providers.signals  # noqa
        except ImportError:
            pass