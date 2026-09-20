from django.urls import path
from .views import (
    OwnerVenuesView,
    OwnerBookingsView,
    BookingActionView,
    OwnerDashboardView,
)

urlpatterns = [
    path('venues/', OwnerVenuesView.as_view(), name='owner-venues'),
    path('bookings/', OwnerBookingsView.as_view(), name='owner-bookings'),
    path('bookings/<int:pk>/<str:action>/', BookingActionView.as_view(), name='booking-action'),
    path('dashboard/', OwnerDashboardView.as_view(), name='owner-dashboard'),
]