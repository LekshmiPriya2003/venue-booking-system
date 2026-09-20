from django.shortcuts import render

# Create your views here.
from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOrganizer

from . import services
from .models import Booking
from .serializers import BookingCreateSerializer


class BookingCreateView(APIView):
    """
    POST /api/bookings/

    The serializer validates shape/type (including that the venue exists);
    services.create_booking() applies the business rules and inserts, under
    a venue lock, in one transaction.
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # After is_valid(raise_exception=True) this is always a plain dict; DRF's
        # own annotation doesn't say so, hence the cast (no runtime effect).
        data = cast("dict[str, Any]", serializer.validated_data)
        try:
            booking = services.create_booking(organizer=request.user, **data)
        except DjangoValidationError as exc:
            # message_dict is field-keyed, so each failure stays distinguishable.
            raise serializers.ValidationError(exc.message_dict) from None
        return Response(
            BookingCreateSerializer(booking).data, status=status.HTTP_201_CREATED
        )


class MyBookingsListView(generics.ListAPIView):
    """GET /api/bookings/my/ — the logged-in organizer's own bookings."""

    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]

    # type: ignore[override] below: DRF's get_queryset has no return annotation,
    # so type checkers infer `Never` and flag every real override. Runtime-safe.
    def get_queryset(self):  # type: ignore[override]
        return Booking.objects.filter(organizer=self.request.user)


class BookingDetailView(generics.RetrieveAPIView):
    """
    GET /api/bookings/<id>/

    Visible to the organizer who made the booking, OR the owner of the
    venue it was booked at. Anyone else gets a 404 — the object simply
    isn't in their queryset, so no 403 that would confirm the booking
    exists at all.
    """

    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]  (see MyBookingsListView)
        user = self.request.user
        return Booking.objects.filter(Q(organizer=user) | Q(venue__owner=user))


class BookingCancelView(APIView):
    """
    POST /api/bookings/<id>/cancel/

    Ownership: only the organizer who made the booking can cancel it (other
    people's bookings are simply not in the queryset, so they get a 404).

    Lifecycle: allowed transitions are defined once, on Booking.ALLOWED_FROM,
    and applied atomically by Booking.transition_to(). A booking that can't
    be cancelled (rejected, already cancelled, or changed by someone else a
    moment ago) gets a specific 400 rather than being silently overwritten.
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    # Per-status messages for bookings that can't be cancelled.
    _REFUSAL_MESSAGES: dict[str, str] = {
        Booking.Status.REJECTED: "This booking was already rejected by the venue owner.",
        Booking.Status.CANCELLED: "This booking has already been cancelled.",
    }

    def post(self, request, pk):
        booking = get_object_or_404(Booking.objects.filter(organizer=request.user), pk=pk)

        if not booking.transition_to(Booking.Status.CANCELLED):
            # Re-read: the status we loaded may be stale if another request won.
            booking.refresh_from_db(fields=["status"])
            message = self._REFUSAL_MESSAGES.get(
                booking.status, "This booking can't be cancelled."
            )
            return Response({"status": [message]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BookingCreateSerializer(booking).data, status=status.HTTP_200_OK)