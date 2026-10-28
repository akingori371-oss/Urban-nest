from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # ---------- Pages ----------
    path("", views.landing, name="landing"),
    # path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),

    # ---------- Auth ----------
    path("auth/login/", TokenObtainPairView.as_view(), name="api_login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),

    # ---------- Bookings ----------
    # path("bookings/", views.house_list, name="houses"),
    path("book/", views.book, name="book"),
    # path("mine/", views.my_bookings, name="my_bookings"),
    # path("card/<int:pk>/", views.booking_card, name="booking_card"),
    # path("favorites/", views.favorites, name="favorites"),

    # # ---------- Reviews ----------
    # path("review/booking/<int:pk>/", views.review_booking, name="review_booking"),
    # path("review/period/<int:pk>/", views.review_period, name="review_period"),

    # ---------- Button actions (POST only) ----------
    path("cancel-booking/<int:pk>/", views.cancel_booking, name="cancel_booking"),
    path("pay-booking/<int:pk>/", views.pay_booking, name="pay_booking"),
    path("pay-period/<int:pk>/", views.pay_period, name="pay_period"),
    path("toggle-favorite/<int:pk>/", views.toggle_favorite, name="toggle_favorite"),

    # ---------- API ----------
    path("api/", include("plots.api.urls")),
]