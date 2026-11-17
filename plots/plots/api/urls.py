
from django.urls import path
from . import api_views as v
from . import manager_views as m
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Authentication
    path("auth/register/", v.register),
    path("auth/login/", v.login_view),
    path("auth/password-reset/request/", v.password_reset_request),
    path("auth/password-reset/verify/", v.password_reset_verify),
    path("auth/password-reset/complete/", v.password_reset_complete),
    path("auth/me/", v.me),
    path("auth/token/refresh/", TokenRefreshView.as_view()),

    # Public houses
    path("houses/", v.house_list),
    path("houses/<int:pk>/", v.house_detail),

    # User property submissions
    path("my-houses/", v.my_houses),
    path("my-houses/<int:pk>/", v.manage_my_house),
    path("my-houses/<int:pk>/toggle/", v.toggle_my_house),

    # Admin property approvals
    path("admin/pending-houses/", v.pending_houses),
    path("admin/houses/<int:pk>/review/", v.review_house),

    # Bookings
    path("bookings/", v.booking_list),
    path("bookings/<int:pk>/", v.booking_detail),
    path("bookings/<int:pk>/cancel/", v.booking_cancel),

    # Notifications
    path("notifications/", v.user_notifications),
    path("notifications/<int:pk>/read/", v.notification_read),

    # Dashboard
    path("dashboard/", v.dashboard),

    # Manager endpoints
    path("manager/dashboard/", m.manager_dashboard),
    path("manager/apartments/", m.manager_houses),
    path("manager/apartments/<int:pk>/", m.manager_house_detail),
    path("manager/apartments/<int:pk>/photos/", m.manager_house_photos),
    path("manager/apartments/<int:pk>/photos/<int:photo_pk>/", m.manager_house_photo_detail),
    path("manager/bookings/", m.manager_bookings),
    path("manager/booking-requests/unread-count/", m.manager_booking_unread_count),
    path("manager/bookings/<int:pk>/", m.manager_booking_detail),
    path("manager/bookings/<int:pk>/approve/", m.manager_booking_approve),
    path("manager/bookings/<int:pk>/reject/", m.manager_booking_reject),
    path("manager/bookings/<int:pk>/clarify/", m.manager_booking_clarify),
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
