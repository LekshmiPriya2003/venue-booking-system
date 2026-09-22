from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

# Teammate imports
from accounts.permissions import IsVenueOwner
from venues.models import Venue
from venues.serializers import VenueSerializer
from bookings.models import Booking
from bookings.serializers import BookingCreateSerializer  # or BookingDetailSerializer
from bookings.services import run_conflict_checks


class OwnerVenuesView(APIView):
    """List all venues managed by the logged-in owner."""
    permission_classes = [permissions.IsAuthenticated, IsVenueOwner]

    def get(self, request):
        venues = Venue.objects.filter(owner=request.user)
        serializer = VenueSerializer(venues, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OwnerBookingsView(APIView):
    """List all bookings across an owner's venues, filterable by status."""
    permission_classes = [permissions.IsAuthenticated, IsVenueOwner]

    def get(self, request):
        bookings = Booking.objects.filter(venue__owner=request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            bookings = bookings.filter(status__iexact=status_filter)

        serializer = BookingCreateSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingActionView(APIView):
    """Approve or reject a booking (POST /api/owner/bookings/<id>/<approve|reject>/)."""
    permission_classes = [permissions.IsAuthenticated, IsVenueOwner]

    def post(self, request, pk, action):
        action = action.lower()
        if action not in ['approve', 'reject']:
            return Response(
                {"error": "Invalid action. Choose 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. 404 security pattern: match Person C's privacy rule
        booking = get_object_or_404(Booking, pk=pk, venue__owner=request.user)

        # 2. Only PENDING bookings can be approved or rejected
        if booking.status != 'PENDING':
            return Response(
                {"error": f"Cannot {action} a booking with status '{booking.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Rejection Logic
        if action == 'reject':
            if not booking.transition_to(Booking.Status.REJECTED):
                return Response(
                    {"error": "This booking is no longer pending."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            self._send_notification(booking, 'rejected')
            return Response({"message": "Booking has been rejected."}, status=status.HTTP_200_OK)

        # Approval Logic: wrapped in select_for_update inside transaction.atomic
        try:
            with transaction.atomic():
                # Lock the venue record during verification to block concurrent approvals
                venue = Venue.objects.select_for_update().get(id=booking.venue_id)

                # Re-run the 5 conflict rules (buffer, active, overlap, blackout, capacity)
                run_conflict_checks(
                    venue=venue,
                    event_date=booking.event_date,
                    start_time=booking.start_time,
                    end_time=booking.end_time,
                    expected_headcount=booking.expected_headcount,
                    exclude_booking_id=booking.id,
                )

                if not booking.transition_to(Booking.Status.CONFIRMED):
                    return Response(
                        {"error": "This booking is no longer pending."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        except DjangoValidationError as e:
            return Response(
                {"error": "Cannot confirm booking.", "details": e.message_dict},
                status=status.HTTP_400_BAD_REQUEST,
            )

        self._send_notification(booking, 'approved')
        return Response({"message": "Booking confirmed successfully."}, status=status.HTTP_200_OK)

    def _send_notification(self, booking, action):
        """Helper to invoke Person A's notification module safely."""
        try:
            from accounts.utils import notify
            notify(user=booking.organizer, action=action, booking=booking)
        except (ImportError, AttributeError):
            pass


class OwnerDashboardView(APIView):
    """Aggregate dashboard metrics across the owner's portfolio."""
    permission_classes = [permissions.IsAuthenticated, IsVenueOwner]

    def get(self, request):
        today = timezone.now().date()
        owner_venues = Venue.objects.filter(owner=request.user)
        owner_bookings = Booking.objects.filter(venue__owner=request.user)

        # Upcoming confirmed bookings
        upcoming_count = owner_bookings.filter(
            status='CONFIRMED',
            event_date__gte=today
        ).count()

        # Total cancellations
        cancelled_count = owner_bookings.filter(status='CANCELLED').count()

        # Venue utilization aggregation
        utilization = owner_venues.annotate(
            total_bookings=Count('bookings')
        ).values('id', 'name', 'total_bookings')

        formatted_utilization = [
            {
                "venue_id": item['id'],
                "venue_name": item['name'],
                "total_bookings": item['total_bookings']
            }
            for item in utilization
        ]

        return Response({
            "upcoming_bookings": upcoming_count,
            "total_cancellations": cancelled_count,
            "venue_utilization": formatted_utilization
        }, status=status.HTTP_200_OK)