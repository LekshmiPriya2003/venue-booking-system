"""
Booking business rules, deliberately free of DRF and request objects so they
can be called from bookings' own views, from the owner app (to re-check a
booking at confirm-time), or from plain unit tests.

Rules live here rather than in the serializer, which only checks shape/type.
Every check raises django.core.exceptions.ValidationError with a field-keyed
message dict.
"""

import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from venues.models import Venue

from .models import Booking

# Minimum gap required between one confirmed booking ending and the next
# one starting on the same venue — time to clean up / re-decorate.
CONFLICT_BUFFER = datetime.timedelta(hours=1)

_ONE_DAY = datetime.timedelta(days=1)


def _to_datetime(event_date, t):
    """Combine a date + time so buffer math can cross midnight."""
    return datetime.datetime.combine(event_date, t)


def _describe_buffer():
    """Human-readable CONFLICT_BUFFER for error messages ('1 hour', '90 minutes')."""
    minutes = int(CONFLICT_BUFFER.total_seconds() // 60)
    hours, remainder = divmod(minutes, 60)
    if remainder == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{minutes} minutes"


def validate_booking_window(event_date, start_time, end_time):
    """Reject dates in the past and time ranges that don't move forward."""
    errors = {}
    if event_date < timezone.localdate():
        errors["event_date"] = "Event date cannot be in the past."
    if end_time <= start_time:
        errors["end_time"] = "End time must be after start time."
    if errors:
        raise DjangoValidationError(errors)


def check_venue_active(venue):
    """Reject bookings against a deactivated (soft-deleted) venue."""
    if not venue.is_active:
        raise DjangoValidationError(
            {"venue": "This venue is not currently accepting bookings."}
        )


def check_blackout_date(venue, event_date):
    """Reject dates the venue has blacked out."""
    if venue.blackout_dates.filter(date=event_date).exists():
        raise DjangoValidationError(
            {"event_date": "This venue is unavailable on the selected date."}
        )


def check_time_conflict(
    venue, event_date, start_time, end_time, exclude_booking_id=None
):
    """
    Reject if the requested slot is closer than CONFLICT_BUFFER to any
    CONFIRMED booking on the same venue, in either direction — not just
    literal overlap. Back-to-back bookings (no gap) are rejected.

    Bookings on the neighbouring days are considered too, so the buffer is
    enforced across midnight (e.g. one ending 23:30 and one starting 00:00
    the next day).

    exclude_booking_id lets the owner app re-validate an existing booking at
    confirm-time without it conflicting with itself.
    """
    padded_start = _to_datetime(event_date, start_time) - CONFLICT_BUFFER
    padded_end = _to_datetime(event_date, end_time) + CONFLICT_BUFFER

    nearby = Booking.objects.filter(
        venue=venue,
        status=Booking.Status.CONFIRMED,
        event_date__range=(event_date - _ONE_DAY, event_date + _ONE_DAY),
    )
    if exclude_booking_id is not None:
        nearby = nearby.exclude(pk=exclude_booking_id)

    for existing in nearby:
        existing_start = _to_datetime(existing.event_date, existing.start_time)
        existing_end = _to_datetime(existing.event_date, existing.end_time)
        if existing_start < padded_end and existing_end > padded_start:
            raise DjangoValidationError(
                {
                    "start_time": (
                        f"This slot is within {_describe_buffer()} of another "
                        "confirmed booking at this venue; a turnaround gap "
                        "is required."
                    )
                }
            )


def check_capacity(venue, expected_headcount):
    """Reject headcounts above the venue's capacity (equal is fine)."""
    if expected_headcount > venue.capacity:
        raise DjangoValidationError(
            {"expected_headcount": f"Exceeds venue capacity of {venue.capacity}."}
        )


def run_conflict_checks(
    venue,
    event_date,
    start_time,
    end_time,
    expected_headcount,
    exclude_booking_id=None,
):
    """
    Run every venue-dependent rule, cheapest first, so an inactive venue or a
    blackout date short-circuits before the pricier overlap query runs.
    Raises DjangoValidationError on the first failure.

    The owner app should call this at confirm-time with
    exclude_booking_id=<the booking>, inside its own transaction.atomic(),
    and then move the status with booking.transition_to(CONFIRMED).
    """
    check_venue_active(venue)
    check_blackout_date(venue, event_date)
    check_time_conflict(
        venue,
        event_date,
        start_time,
        end_time,
        exclude_booking_id=exclude_booking_id,
    )
    check_capacity(venue, expected_headcount)


@transaction.atomic
def create_booking(
    *,
    organizer,
    venue,
    event_title,
    event_category,
    event_date,
    start_time,
    end_time,
    expected_headcount,
):
    """
    Validate and create a PENDING booking.

    The venue is locked and all checks run inside the SAME atomic block as
    the insert. Doing the checks outside it would reopen the check-then-write
    race this block exists to close. select_for_update() is a no-op on SQLite
    (there, protection comes from the database serializing write
    transactions — see DATABASES OPTIONS transaction_mode), but it becomes
    real row-level locking on Postgres/MySQL.

    Raises DjangoValidationError if any rule fails.
    """
    validate_booking_window(event_date, start_time, end_time)
    locked_venue = Venue.objects.select_for_update().get(pk=venue.pk)
    run_conflict_checks(
        locked_venue, event_date, start_time, end_time, expected_headcount
    )
    return Booking.objects.create(
        organizer=organizer,
        venue=locked_venue,
        event_title=event_title,
        event_category=event_category,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        expected_headcount=expected_headcount,
    )