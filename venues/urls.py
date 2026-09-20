from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LocationViewSet,
    VenueViewSet,
    VenueBlackoutDateViewSet,
)


router = DefaultRouter()

router.register('locations', LocationViewSet, basename='location')
router.register('venues', VenueViewSet, basename='venue')
router.register(
    'blackout-dates',
    VenueBlackoutDateViewSet,
    basename='blackout-date'
)


urlpatterns = [
    path('', include(router.urls)),
]