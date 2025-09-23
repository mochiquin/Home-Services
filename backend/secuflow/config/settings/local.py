from .base import *  # noqa

DEBUG = True

# Override logging for development - enable DEBUG level for TNM
LOGGING['loggers']['tnm_integration']['level'] = 'DEBUG'
LOGGING['loggers']['tnm_integration.services']['level'] = 'DEBUG'
LOGGING['loggers']['tnm_integration.views']['level'] = 'DEBUG'

# Add TNM console logging for development
LOGGING['handlers']['tnm_console'] = {
    'class': 'logging.StreamHandler',
    'formatter': 'simple',
    'level': 'DEBUG',
}

# Make sure TNM logs also go to console in development
LOGGING['loggers']['tnm_integration']['handlers'] = ['console', 'tnm_console']
LOGGING['loggers']['tnm_integration.services']['handlers'] = ['console', 'tnm_console']
LOGGING['loggers']['tnm_integration.views']['handlers'] = ['console', 'tnm_console']

