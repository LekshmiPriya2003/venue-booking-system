from rest_framework import serializers

class VenueUtilizationSerializer(serializers.Serializer):
    venue_id = serializers.IntegerField()
    venue_name = serializers.CharField()
    total_bookings = serializers.IntegerField()

class OwnerDashboardSerializer(serializers.Serializer):
    upcoming_bookings = serializers.IntegerField()
    total_cancellations = serializers.IntegerField()
    venue_utilization = VenueUtilizationSerializer(many=True)