from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.BookingCreateView.as_view(), name="booking-create"),
    path("my/", views.MyBookingsListView.as_view(), name="booking-list-mine"),
    path("<int:pk>/", views.BookingDetailView.as_view(), name="booking-detail"),
    path("<int:pk>/cancel/", views.BookingCancelView.as_view(), name="booking-cancel"),
]