import django_filters
from .models import Venue


class VenueFilter(django_filters.FilterSet):

    category = django_filters.CharFilter(
        field_name="category",
        lookup_expr="iexact"
    )

    location = django_filters.NumberFilter(
        field_name="location_id"
    )

    min_capacity = django_filters.NumberFilter(
        field_name="capacity",
        lookup_expr="gte"
    )

    class Meta:
        model = Venue
        fields = ["category", "location", "min_capacity"]