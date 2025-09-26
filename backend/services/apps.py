from django.apps import AppConfig


class ServicesConfig(AppConfig):
    """Configuration for the services app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services'
    verbose_name = 'Services'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import services.signals  # noqa
        except ImportError:
            pass

