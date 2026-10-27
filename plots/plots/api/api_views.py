from django.contrib.auth import authenticate
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import House, Booking, PaymentPeriod, Announcement
from .serializers import (RegisterSerializer, HouseSerializer,
                          BookingSerializer, PaymentPeriodSerializer)


def err(msg, code=400):
    return Response({"detail": msg}, status=code)


# ---------- Auth ----------
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = s.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "username": user.username}, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(username=request.data.get("username"),
                        password=request.data.get("password"))
    if user is None:
        return err("Invalid username or password.", 401)
    token, _ = Token.objects.get_or_create(user=user)
    user_logged_in.send(sender=user.__class__, request=request, user=user)  # records a LoginEvent
    return Response({"token": token.key, "username": user.username,
                     "is_superuser": user.is_superuser})


@api_view(["GET"])
def me(request):
    u = request.user
    return Response({"id": u.id, "username": u.username, "email": u.email})


# ---------- Houses ----------
@api_view(["GET"])
def house_list(request):
    qs = House.objects.annotate(avg_rating=Avg("reviews__rating"),
                                review_count=Count("reviews"))
    try:
        cin = parse_date(request.query_params.get("check_in") or "")
        cout = parse_date(request.query_params.get("check_out") or "")
    except ValueError:
        return err("Dates must be YYYY-MM-DD.")
    if cin and cout:
        if cout <= cin:
            return err("check_out must be after check_in.")
        busy = Booking.objects.filter(status="confirmed", check_in__lt=cout,
                                      check_out__gt=cin).values_list("house_id", flat=True)
        qs = qs.exclude(id__in=busy)
    return Response(HouseSerializer(qs, many=True).data)


# ---------- Bookings ----------
def own_booking(request, pk):
    return get_object_or_404(Booking.objects.select_related("house"),
                             pk=pk, user=request.user)   # not yours = 404


@api_view(["GET", "POST"])
def booking_list(request):
    if request.method == "GET":
        qs = Booking.objects.filter(user=request.user).select_related("house").order_by("-check_in")
        return Response(BookingSerializer(qs, many=True).data)

    s = BookingSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    total = (d["check_out"] - d["check_in"]).days * d["house"].price_per_night
    with transaction.atomic():
        booking = s.save(user=request.user, total_price=total)
        if booking.is_long:
            booking.create_periods()
    return Response(BookingSerializer(booking).data, status=201)


@api_view(["POST"])
def booking_cancel(request, pk):
    b = own_booking(request, pk)
    if b.status == "cancelled":
        return err("Already cancelled.")
    b.status = "cancelled"
    b.save()
    return Response(BookingSerializer(b).data)


@api_view(["POST"])
def booking_pay(request, pk):
    b = own_booking(request, pk)
    if b.status != "confirmed":
        return err("Cancelled bookings can't be paid.")
    if b.is_long:
        return err("Long stays are paid per period.")
    if b.paid:
        return err("Already paid.")
    b.paid, b.paid_at = True, timezone.now()
    b.save()
    return Response(BookingSerializer(b).data)


@api_view(["GET"])
def booking_periods(request, pk):
    return Response(PaymentPeriodSerializer(own_booking(request, pk).periods.all(), many=True).data)


@api_view(["POST"])
def period_pay(request, pk):
    p = get_object_or_404(PaymentPeriod.objects.select_related("booking"),
                          pk=pk, booking__user=request.user)
    if p.booking.status != "confirmed":
        return err("Cancelled bookings can't be paid.")
    if p.paid:
        return err("Already paid.")
    p.paid, p.paid_at = True, timezone.now()
    p.save()
    return Response(PaymentPeriodSerializer(p).data)


# ---------- Dashboard ----------
@api_view(["GET"])
def dashboard(request):
    due = PaymentPeriod.objects.filter(booking__user=request.user,
                                       booking__status="confirmed", paid=False).count()
    ann = [{"title": a.title, "message": a.message, "created_at": a.created_at}
           for a in Announcement.objects.all()[:5]]
    return Response({"payments_due": due, "announcements": ann})