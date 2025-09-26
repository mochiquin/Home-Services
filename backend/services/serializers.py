"""
Services API Serializers

This module provides serializers for Home Services API.
"""

from rest_framework import serializers
from .models import ServiceCategory, Service, ServiceRequirement, ServiceArea


class ServiceCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for ServiceCategory model.
    """

    services_count = serializers.IntegerField(source='services.count', read_only=True)

    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'icon', 'is_active',
            'sort_order', 'services_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'services_count']


class ServiceRequirementSerializer(serializers.ModelSerializer):
    """
    Serializer for ServiceRequirement model.
    """

    class Meta:
        model = ServiceRequirement
        fields = ['id', 'requirement', 'is_mandatory', 'sort_order']


class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Service model.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    requirements = ServiceRequirementSerializer(many=True, read_only=True)
    price_unit_display = serializers.CharField(source='get_price_unit_display', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'category', 'category_name', 'description',
            'base_price', 'price_unit', 'price_unit_display',
            'estimated_duration_minutes', 'requires_quote',
            'is_active', 'image', 'requirements',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create service with requirements if provided."""
        requirements_data = self.initial_data.get('requirements', [])
        service = Service.objects.create(**validated_data)

        for req_data in requirements_data:
            ServiceRequirement.objects.create(service=service, **req_data)

        return service


class ServiceAreaSerializer(serializers.ModelSerializer):
    """
    Serializer for ServiceArea model.
    """

    class Meta:
        model = ServiceArea
        fields = [
            'id', 'name', 'state', 'country', 'postal_code',
            'latitude', 'longitude', 'radius_km', 'is_active'
        ]
        read_only_fields = ['id']


# Simplified serializers for lists and selections
class ServiceCategoryListSerializer(serializers.ModelSerializer):
    """Simplified serializer for service category lists."""

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'icon', 'sort_order']


class ServiceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for service lists."""

    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'category_name', 'base_price',
            'price_unit', 'requires_quote', 'image'
        ]