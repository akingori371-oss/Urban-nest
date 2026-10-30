from django.urls import path
from . import api_views as v
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("auth/register/", v.register),
    path("auth/login/", v.login_view),
    path("auth/me/", v.me),
    path("houses/", v.house_list),
    path("bookings/", v.booking_list),
    path("bookings/<int:pk>/cancel/", v.booking_cancel),
    path("bookings/<int:pk>/pay/", v.booking_pay),
    path("bookings/<int:pk>/periods/", v.booking_periods),
    path("periods/<int:pk>/pay/", v.period_pay),
    path("dashboard/", v.dashboard),
    path("pay/<str:kind>/<int:pk>/", v.pay_mock),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
]