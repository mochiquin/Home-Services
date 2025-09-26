"""
Services API Views

This module provides API views for Home Services.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import ServiceCategory, Service, ServiceRequirement, ServiceArea
from .serializers import (
    ServiceCategorySerializer,
    ServiceSerializer,
    ServiceRequirementSerializer,
    ServiceAreaSerializer
)


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service categories.
    """

    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['sort_order', 'name', 'created_at']
    ordering = ['sort_order', 'name']


class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing services.
    """

    queryset = Service.objects.select_related('category').all()
    serializer_class = ServiceSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active', 'requires_quote', 'price_unit']
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['name', 'base_price', 'created_at']
    ordering = ['category__sort_order', 'name']

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular services based on booking count."""
        # This would typically involve aggregating booking data
        # For now, return top services by category
        popular_services = self.get_queryset()[:10]
        serializer = self.get_serializer(popular_services, many=True)
        return Response(serializer.data)


class ServiceAreaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service areas.
    """

    queryset = ServiceArea.objects.all()
    serializer_class = ServiceAreaSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    filterset_fields = ['state', 'country', 'is_active']
    search_fields = ['name', 'state', 'postal_code']
    ordering_fields = ['name', 'state']
    ordering = ['state', 'name']