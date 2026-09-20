from rest_framework import serializers

from .models import Booking


class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Shape/type validation for incoming data, and the response format for
    every booking endpoint (create, list, detail, cancel).

    Business rules (dates, availability, capacity, conflicts) are NOT here —
    they live in services.py. Creation goes through services.create_booking()
    rather than serializer.save(), so the venue lock and the checks share one
    transaction with the insert.
    """

    class Meta:
        model = Booking
        fields = [
            "id",
            "organizer",
            "venue",
            "event_title",
            "event_category",
            "event_date",
            "start_time",
            "end_time",
            "expected_headcount",
            "status",
            "booked_at",
        ]
        read_only_fields = ["id", "organizer", "status", "booked_at"]
        extra_kwargs = {"expected_headcount": {"min_value": 1}}