from django.contrib import admin
from .models import ServiceCategory, Service, ServiceRequirement, ServiceArea


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for ServiceCategory model."""

    list_display = ['name', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'sort_order']
    ordering = ['sort_order', 'name']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Admin configuration for Service model."""

    list_display = [
        'name', 'category', 'base_price', 'price_unit',
        'is_active', 'requires_quote', 'created_at'
    ]
    list_filter = ['category', 'is_active', 'requires_quote', 'price_unit', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    list_editable = ['is_active', 'requires_quote']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'image')
        }),
        ('Pricing', {
            'fields': ('base_price', 'price_unit', 'requires_quote')
        }),
        ('Service Details', {
            'fields': ('estimated_duration_minutes',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceRequirement)
class ServiceRequirementAdmin(admin.ModelAdmin):
    """Admin configuration for ServiceRequirement model."""

    list_display = ['service', 'requirement', 'is_mandatory', 'sort_order']
    list_filter = ['is_mandatory', 'service__category']
    search_fields = ['requirement', 'service__name']
    list_editable = ['is_mandatory', 'sort_order']
    ordering = ['service', 'sort_order']


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    """Admin configuration for ServiceArea model."""

    list_display = ['name', 'state', 'country', 'postal_code', 'is_active']
    list_filter = ['state', 'country', 'is_active']
    search_fields = ['name', 'state', 'postal_code']
    list_editable = ['is_active']
    ordering = ['state', 'name']