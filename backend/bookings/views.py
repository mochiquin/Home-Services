from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from common.decorators import api_exception_handler

from .models import Booking, BookingStatusHistory
from .serializers import (
    BookingSerializer,
    BookingListSerializer,
    BookingStatusHistorySerializer
)


class BookingViewSet(viewsets.ModelViewSet):
    """Simple booking API with CRUD operations."""

    queryset = Booking.objects.select_related('customer', 'provider', 'service').all()
    serializer_class = BookingSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        return BookingSerializer

    def get_queryset(self):
        """Filter bookings based on user role."""
        user = self.request.user
        if user.is_authenticated:
            # Customer sees their own bookings
            if hasattr(user, 'bookings'):
                return self.queryset.filter(customer=user)
            # Provider sees their assigned bookings
            elif hasattr(user, 'provider_profile'):
                return self.queryset.filter(provider=user.provider_profile)
        return self.queryset

    @action(detail=True, methods=['post'])
    @api_exception_handler
    def update_status(self, request, pk=None):
        """Update booking status with history tracking."""
        booking = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')

        if not new_status:
            return Response({'error': 'status required'}, status=400)

        if new_status not in dict(Booking.STATUS_CHOICES):
            return Response({'error': 'invalid status'}, status=400)

        # Create status history
        BookingStatusHistory.objects.create(
            booking=booking,
            old_status=booking.status,
            new_status=new_status,
            changed_by=request.user,
            reason=reason
        )

        # Update booking
        booking.status = new_status
        if new_status == 'completed':
            booking.completed_at = timezone.now()
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    @api_exception_handler
    def status_history(self, request, pk=None):
        """Get booking status history."""
        booking = self.get_object()
        history = booking.status_history.all()
        serializer = BookingStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @api_exception_handler
    def by_status(self, request):
        """Filter bookings by status."""
        status_filter = request.query_params.get('status')
        if not status_filter:
            return Response({'error': 'status parameter required'}, status=400)

        bookings = self.get_queryset().filter(status=status_filter)
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)