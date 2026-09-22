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
        read_only_fields = ['owner', 'created_at']


class VenueBlackoutDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueBlackoutDate
        fields = '__all__'
        