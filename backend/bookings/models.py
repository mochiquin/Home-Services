"""
Bookings Models

This module handles service bookings and appointments.
"""

import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    """
    Main booking model for home services.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    provider = models.ForeignKey('providers.ServiceProvider', on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey('services.Service', on_delete=models.CASCADE, related_name='bookings')

    # Booking details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')

    # Scheduling
    requested_date = models.DateField()
    requested_time = models.TimeField()
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    confirmed_date = models.DateField(null=True, blank=True)
    confirmed_time = models.TimeField(null=True, blank=True)

    # Location
    service_address = models.TextField()
    service_city = models.CharField(max_length=100)
    service_state = models.CharField(max_length=100)
    service_postal_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Pricing
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Additional information
    customer_notes = models.TextField(blank=True, help_text="Special instructions from customer")
    provider_notes = models.TextField(blank=True, help_text="Internal notes from provider")

    # Contact information
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['requested_date', 'requested_time']),
            models.Index(fields=['service_city', 'service_state']),
        ]

    def __str__(self) -> str:
        return f"Booking {self.id} - {self.service.name} for {self.customer.get_full_name()}"

    @property
    def total_estimated_cost(self):
        """Calculate total estimated cost including any additional fees."""
        return self.quoted_price


class BookingStatusHistory(models.Model):
    """
    Track status changes for bookings.
    """

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self) -> str:
        return f"{self.booking.id}: {self.old_status} -> {self.new_status}"
