"""
Providers API Views

This module provides API views for Service Providers.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated

from .models import ServiceProvider, ProviderService, ProviderAvailability, ProviderDocument


class ServiceProviderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service providers.
    """

    queryset = ServiceProvider.objects.select_related('user').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['business_name', 'user__first_name', 'user__last_name', 'city']
    ordering_fields = ['average_rating', 'created_at']
    ordering = ['-average_rating']

    def get_queryset(self):
        """Filter to show only active and verified providers for non-staff users."""
        queryset = super().get_queryset()

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True, is_verified=True)

        return queryset

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get providers near a specific location."""
        # This would implement geospatial search
        # For now, return all providers
        providers = self.get_queryset()[:10]
        return Response([])  # Placeholder


class ProviderServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing services offered by providers.
    """

    queryset = ProviderService.objects.select_related('provider', 'service').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['service__name', 'provider__business_name']
    ordering_fields = ['base_price', 'years_of_experience']
    ordering = ['base_price']