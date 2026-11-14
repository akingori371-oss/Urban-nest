
from django.urls import path
from . import api_views as v
from . import manager_views as m
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Authentication
    path("auth/register/", v.register),
    path("auth/login/", v.login_view),
    path("auth/me/", v.me),
    path("auth/token/refresh/", TokenRefreshView.as_view()),

    # Houses
    path("houses/", v.house_list),
    path("houses/<int:pk>/", v.house_detail),

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

    # Manager endpoints
    path("manager/dashboard/", m.manager_dashboard),
    path("manager/apartments/", m.manager_houses),
    path("manager/apartments/<int:pk>/", m.manager_house_detail),
    path("manager/apartments/<int:pk>/photos/", m.manager_house_photos),
    path("manager/apartments/<int:pk>/photos/<int:photo_pk>/", m.manager_house_photo_detail),
    path("manager/bookings/", m.manager_bookings),
    path("manager/bookings/<int:pk>/", m.manager_booking_detail),
    path("manager/payments/", m.manager_payments),
    path("manager/announcements/", m.manager_announcements),
    path("manager/announcements/<int:pk>/", m.manager_announcement_detail),
    path("manager/tenants/", m.manager_tenants),
    path("manager/tenants/<int:pk>/", m.manager_tenant_detail),
    path("manager/invitations/", m.manager_invitations),
    path("manager/invitations/<int:pk>/", m.manager_invitation_cancel),
    path("manager/invitations/accept/<str:token>/", m.accept_manager_invitation),
    path("manager/managers/", m.manager_list),
    path("manager/managers/<int:pk>/", m.manager_remove),
]

