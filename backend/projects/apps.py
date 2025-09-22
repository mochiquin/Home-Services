from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Configuration for the projects app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'
    verbose_name = 'Projects'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import projects.signals  # noqa
        except ImportError:
            pass

