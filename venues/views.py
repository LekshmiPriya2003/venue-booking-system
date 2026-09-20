from accounts.permissions import IsVenueOwnerObjectOwner
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend

from .models import Location, Venue, VenueBlackoutDate
from .serializers import (
    LocationSerializer,
    VenueSerializer,
    VenueBlackoutDateSerializer,
)
from .filters import VenueFilter


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = VenueFilter
    permission_classes = [IsVenueOwnerObjectOwner]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

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
# Create your views here.
