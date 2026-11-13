
from django.urls import path
from . import api_views as v
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Authentication
    path("auth/register/", v.register),
    path("auth/login/", v.login_view),
    path("auth/me/", v.me),
    path("auth/token/refresh/", TokenRefreshView.as_view()),

    # Houses
    path("houses/", v.house_list),

    # Bookings
    path("bookings/", v.booking_list),
    path("bookings/<int:pk>/cancel/", v.booking_cancel),
    path("bookings/<int:pk>/periods/", v.booking_periods),

    # Payments
    path("pay/<str:kind>/<int:pk>/", v.pay_mock),
    path("payments/<int:pk>/", v.payment_status),
    path("mpesa/callback/", v.mpesa_callback),

    # Dashboard
    path("dashboard/", v.dashboard),
]
