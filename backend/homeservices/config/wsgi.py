import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secuflow.config.settings.prod')

application = get_wsgi_application()


