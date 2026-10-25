from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", views.landing, name="landing"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),

    path("accounts/login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.signup, name="signup"),

    path("bookings/", views.house_list, name="houses"),
    path("bookings/book/", views.book, name="book"),
    path("bookings/mine/", views.my_bookings, name="my_bookings"),
    path("bookings/card/<int:pk>/", views.booking_card, name="booking_card"),
    path("bookings/favorites/", views.Favorite, name="favorites"),
    path("bookings/review/booking/<int:pk>/", views.review_booking, name="review_booking"),
    path("bookings/review/period/<int:booking_pk>/<int:period_pk>/", views.review_period, name="review_period"),
    path("bookings/cancel/<int:pk>/", views.cancel_booking, name="cancel_booking"),
    path("bookings/pay/booking/<int:pk>/", views.pay_booking, name="pay_booking"),
    path("bookings/pay/period/<int:booking_pk>/<int:period_pk>/", views.pay_period, name="pay_period"),
    path("bookings/favorite/<int:pk>/", views.toggle_favorite, name="toggle_favorite"),
]