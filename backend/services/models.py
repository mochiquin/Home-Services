"""
Home Services Models

This module provides models for Service categories and individual services.
"""

import uuid
from django.db import models


class ServiceCategory(models.Model):
    """
    Categories for organizing home services.

    Examples: Cleaning, Plumbing, Electrical, HVAC, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class name")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Service Categories'

    def __str__(self) -> str:
        return self.name


class Service(models.Model):
    """
    Individual home services that can be booked.

    Examples: House Cleaning, Toilet Repair, Light Installation, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    description = models.TextField()

    # Pricing information (base pricing, can be overridden by providers)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_unit = models.CharField(
        max_length=20,
        choices=[
            ('fixed', 'Fixed Price'),
            ('hourly', 'Per Hour'),
            ('sqft', 'Per Square Foot'),
            ('room', 'Per Room'),
        ],
        default='fixed'
    )

    # Service details
    estimated_duration_minutes = models.IntegerField(null=True, blank=True)
    requires_quote = models.BooleanField(default=False, help_text="Service requires custom quote")

    # Status
    is_active = models.BooleanField(default=True)

    # SEO and display
    image = models.ImageField(upload_to='service_images/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self) -> str:
        return f"{self.category.name} - {self.name}"


class ServiceRequirement(models.Model):
    """
    Requirements or prerequisites for a service.

    Example: "Access to main water valve", "Clear pathway to work area"
    """

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='requirements')
    requirement = models.CharField(max_length=255)
    is_mandatory = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'requirement']

    def __str__(self) -> str:
        return f"{self.service.name} - {self.requirement}"


class ServiceArea(models.Model):
    """
    Geographic areas where services are available.
    """

    name = models.CharField(max_length=100)  # City, Region, ZIP code
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='USA')
    postal_code = models.CharField(max_length=20, blank=True)

    # Geographic boundaries (simplified)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    radius_km = models.IntegerField(default=50)

    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['name', 'state']),
            models.Index(fields=['postal_code']),
        ]

    def __str__(self) -> str:
        return f"{self.name}, {self.state}"