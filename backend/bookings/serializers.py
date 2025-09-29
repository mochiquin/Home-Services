from rest_framework import serializers
from .models import Booking, BookingStatusHistory


class BookingSerializer(serializers.ModelSerializer):
    """Simple booking serializer with all fields."""

    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'completed_at')


class BookingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing bookings."""

    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'status', 'priority', 'requested_date', 'requested_time',
            'quoted_price', 'customer_name', 'provider_name', 'service_name',
            'service_address', 'service_city', 'created_at'
        ]


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    """Simple status history serializer."""

    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = BookingStatusHistory
        fields = '__all__'
        read_only_fields = ('id', 'changed_at')