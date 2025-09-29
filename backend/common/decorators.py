"""
Global exception handling decorators following KISS principle.
Simple, unified error handling for all API endpoints.
"""

import logging
from functools import wraps
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def api_exception_handler(view_func):
    """
    Simple decorator for API exception handling.
    Replaces repetitive try-catch blocks in views.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)

        except ValidationError as e:
            logger.warning(f"Validation error in {view_func.__name__}", extra={
                'user_id': getattr(request.user, 'id', None),
                'error': str(e),
                'ip_address': request.META.get('REMOTE_ADDR')
            })
            return Response({
                'error': str(e),
                'error_code': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)

        except PermissionError as e:
            logger.warning(f"Permission denied in {view_func.__name__}", extra={
                'user_id': getattr(request.user, 'id', None),
                'error': str(e),
                'ip_address': request.META.get('REMOTE_ADDR')
            })
            return Response({
                'error': 'Permission denied',
                'error_code': 'PERMISSION_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            logger.error(f"System error in {view_func.__name__}", extra={
                'user_id': getattr(request.user, 'id', None),
                'error': str(e),
                'ip_address': request.META.get('REMOTE_ADDR')
            }, exc_info=True)
            return Response({
                'error': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return wrapper


def authenticated_api(view_func):
    """
    Simple decorator combining authentication check and exception handling.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentication required',
                'error_code': 'AUTHENTICATION_REQUIRED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        return api_exception_handler(view_func)(request, *args, **kwargs)

    return wrapper


def log_api_call(view_func):
    """
    Simple logging decorator for API calls.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        logger.info(f"API call: {view_func.__name__}", extra={
            'user_id': getattr(request.user, 'id', None),
            'method': request.method,
            'path': request.path,
            'ip_address': request.META.get('REMOTE_ADDR')
        })
        return view_func(request, *args, **kwargs)

    return wrapper