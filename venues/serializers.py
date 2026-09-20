from rest_framework import serializers
from .models import Location, Venue, VenueBlackoutDate


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'


class VenueBlackoutDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueBlackoutDate
        fields = '__all__'
        