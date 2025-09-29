"""
KISS Services API - Simple and clean views.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from common.decorators import api_exception_handler

from .models import ServiceCategory, Service
from .serializers import (
    ServiceCategorySerializer,
    ServiceSerializer,
    ServiceCategoryListSerializer,
    ServiceListSerializer
)


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """Simple service categories API."""

    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceCategoryListSerializer
        return ServiceCategorySerializer


class ServiceViewSet(viewsets.ModelViewSet):
    """Simple services API."""

    queryset = Service.objects.select_related('category').filter(is_active=True)
    serializer_class = ServiceSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceListSerializer
        return ServiceSerializer

    @action(detail=False, methods=['get'])
    @api_exception_handler
    def by_category(self, request):
        """Get services by category ID."""
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response({'error': 'category_id required'}, status=400)

        services = self.get_queryset().filter(category_id=category_id)
        serializer = ServiceListSerializer(services, many=True)
        return Response(serializer.data)