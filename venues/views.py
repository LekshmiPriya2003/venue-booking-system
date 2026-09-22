from accounts.permissions import IsVenueOwner, IsVenueOwnerObjectOwner
from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Location, Venue, VenueBlackoutDate
from .serializers import (
    LocationSerializer,
    VenueSerializer,
    VenueBlackoutDateSerializer,
)
from .filters import VenueFilter


class LocationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Reference data: anyone signed in can read; only venue owners can add.

    No update/delete: Venue.location is PROTECT, so deleting a used location
    would 500, and editing a shared city/state would rename it for every venue.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsVenueOwner()]
        return [IsAuthenticated()]

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = VenueFilter
    permission_classes = [IsVenueOwnerObjectOwner]

    def get_queryset(self):
        qs = Venue.objects.all()
        if self.action == 'list':
            # Search results: active venues, plus the caller's own inactive ones.
            qs = qs.filter(Q(is_active=True) | Q(owner=self.request.user))
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        # Soft delete: Booking.venue is PROTECT, so a hard delete would 500
        # (and would destroy booking history).
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class VenueBlackoutDateViewSet(viewsets.ModelViewSet):
    queryset = VenueBlackoutDate.objects.all()
    serializer_class = VenueBlackoutDateSerializer
    permission_classes = [IsVenueOwnerObjectOwner]

    def perform_create(self, serializer):
        venue = serializer.validated_data['venue']

        if venue.owner != self.request.user:
            raise PermissionDenied(
                "You can only add blackout dates for your own venues."
            )

        serializer.save()

    def perform_update(self, serializer):
        # perform_create checks ownership; updates must too, otherwise an owner
        # can re-point a blackout date at someone else's venue.
        venue = serializer.validated_data.get('venue', serializer.instance.venue)
        if venue.owner != self.request.user:
            raise PermissionDenied(
                "You can only manage blackout dates for your own venues."
            )
        serializer.save()
