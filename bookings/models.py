from django.db import models
from django.utils import timezone


class Booking(models.Model):
    """
    A single source of truth for booking status and event-category values,
    per shared-data-model.md. Other apps (owner) import Booking.Status
    rather than redefining the strings.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    class EventCategory(models.TextChoices):
        WEDDING = "WEDDING", "Wedding"
        CORPORATE = "CORPORATE", "Corporate"
        CONFERENCE = "CONFERENCE", "Conference"
        MEETUP = "MEETUP", "Meetup"
        CONCERT = "CONCERT", "Concert"
        OTHER = "OTHER", "Other"

    # Booking lifecycle (booking-module.md): target status -> the statuses it
    # may be entered from. Every app that changes a booking's status (bookings
    # for cancel, owner for confirm/reject) goes through transition_to(), so
    # this table is the only place the lifecycle is defined.
    ALLOWED_FROM = {
        Status.CONFIRMED: (Status.PENDING,),
        Status.REJECTED: (Status.PENDING,),
        Status.CANCELLED: (Status.PENDING, Status.CONFIRMED),
    }

    organizer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    venue = models.ForeignKey(
        "venues.Venue",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    # Type-checker hint only: Django adds venue_id itself, but Pylance can't
    # see auto-generated FK attributes. No column or field is created here.
    venue_id: int
    event_title = models.CharField(max_length=255)
    event_category = models.CharField(max_length=50, choices=EventCategory.choices)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    expected_headcount = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-booked_at"]
        constraints = [
            # Backstop for the API-level checks: bad rows can't get in through
            # the admin, a shell, or a code path that skips the serializer.
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="booking_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(expected_headcount__gte=1),
                name="booking_headcount_at_least_one",
            ),
        ]
        indexes = [
            # Serves the conflict check, which filters on exactly these columns.
            models.Index(
                fields=["venue", "event_date", "status"],
                name="booking_slot_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_title} @ venue={self.venue_id} ({self.status})"

    def transition_to(self, new_status):
        """
        Move the booking to new_status if the lifecycle allows it.

        Returns True if the transition happened, False if the booking's
        *current database status* doesn't permit it (already cancelled,
        already decided, or another request got there first).

        The check and the write are a single conditional UPDATE, so this is
        safe against stale in-memory copies and concurrent requests without
        needing a row lock (which SQLite doesn't have anyway). Assigning
        `booking.status = ...` and calling save() does NOT have that
        guarantee and shouldn't be used for lifecycle changes.
        """
        allowed_from = self.ALLOWED_FROM.get(new_status, ())
        now = timezone.now()
        # .update() bypasses auto_now, so updated_at is set explicitly.
        changed = Booking.objects.filter(
            pk=self.pk, status__in=allowed_from
        ).update(status=new_status, updated_at=now)
        if changed:
            self.status = new_status
            self.updated_at = now
        return bool(changed)