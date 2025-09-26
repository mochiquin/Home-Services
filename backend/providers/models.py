from django.db import models
from django.conf import settings
from services.models import Service


class ServiceProvider(models.Model):
    """A service provider who offers home services."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='provider_profile')
    business_name = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Business details
    license_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_verified = models.BooleanField(default=False)
    background_check_verified = models.BooleanField(default=False)

    # Ratings
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)

    # Availability
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_name(self):
        """Return business name if available, otherwise user's full name."""
        return self.business_name if self.business_name else self.user.get_full_name()

    class Meta:
        indexes = [
            models.Index(fields=["city"], name="idx_provider_city"),
            models.Index(fields=["is_active", "is_verified"], name="idx_provider_status"),
            models.Index(fields=["average_rating"], name="idx_provider_rating"),
        ]

    def __str__(self) -> str:
        return self.display_name or self.user.username

class ProviderService(models.Model):
    """Services offered by a provider."""

    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="offered_services")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Experience and qualifications
    years_of_experience = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    certifications = models.TextField(blank=True, help_text="List of relevant certifications")

    # Availability
    is_available = models.BooleanField(default=True)
    max_distance_km = models.IntegerField(default=50, help_text="Maximum service distance in kilometers")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "service"], name="uq_provider_service"),
        ]
        indexes = [
            models.Index(fields=["service", "is_available"], name="idx_provider_service_available"),
            models.Index(fields=["provider", "base_price"], name="idx_provider_service_price"),
        ]

    def __str__(self) -> str:
        return f"{self.provider.display_name} - {self.service.name}"

class ProviderAvailability(models.Model):
    """Provider's availability schedule."""

    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="availability")
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "day_of_week"], name="uq_provider_availability"),
        ]
        indexes = [
            models.Index(fields=["provider", "day_of_week"], name="idx_provider_availability"),
        ]

    def __str__(self) -> str:
        return f"{self.provider.display_name} - {self.get_day_of_week_display()}"

class ProviderDocument(models.Model):
    """Documents uploaded by providers for verification."""

    DOCUMENT_TYPES = [
        ('license', 'Business License'),
        ('insurance', 'Insurance Certificate'),
        ('certification', 'Professional Certification'),
        ('id', 'Identification Document'),
        ('background_check', 'Background Check'),
    ]

    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='provider_documents/%Y/%m/')
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["provider", "document_type"], name="idx_provider_document_type"),
        ]

    def __str__(self) -> str:
        return f"{self.provider.display_name} - {self.get_document_type_display()}"
