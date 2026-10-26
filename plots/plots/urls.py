
from django.urls import path
from . import views

urlpatterns = [
    # Landing page
    path("", views.landing, name="landing"),

    # Apartment booking
    path("book/", views.book, name="book"),
    path("cancel-booking/<int:pk>/", views.cancel_booking, name="cancel_booking"),
    path("pay-booking/<int:pk>/", views.pay_booking, name="pay_booking"),
    path("pay-period/<int:pk>/", views.pay_period, name="pay_period"),

    # Favorites
    path("toggle-favorite/<int:pk>/", views.toggle_favorite, name="toggle_favorite"),

    # Analytics
    path("analytics/", views.analytics, name="analytics"),
]
