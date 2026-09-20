from django.db import models


class Location(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.city}, {self.state}"


class Venue(models.Model):
    class Category(models.TextChoices):
        WEDDING = "WEDDING", "Wedding"
        CORPORATE = "CORPORATE", "Corporate"
        CONFERENCE = "CONFERENCE", "Conference"
        MEETUP = "MEETUP", "Meetup"
        CONCERT = "CONCERT", "Concert"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    capacity = models.PositiveIntegerField()
    category = models.CharField(
        max_length=50,
        choices=Category.choices
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="venues"
    )
    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="venues"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class VenueBlackoutDate(models.Model):
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="blackout_dates"
    )
    date = models.DateField()
    reason = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return f"{self.venue.name} - {self.date}"

# Create your models here.
