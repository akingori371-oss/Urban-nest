import random
import re
 
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
 
from ..models import House, Booking, PaymentPeriod, Announcement
from .serializers import (RegisterSerializer, HouseSerializer,
                          BookingSerializer, PaymentPeriodSerializer)
 
 
def err(msg, code=400):
    return Response({"detail": msg}, status=code)
 
 
class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.is_superuser)
 
 
# ---------- Auth ----------
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = s.save()
    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "username": user.username,
    }, status=201)
 
 
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password")
    if not email or not password:
        return err("Send both email and password.")
 
    found = get_user_model().objects.filter(email__iexact=email).first()
    user = authenticate(username=found.username, password=password) if found else None
    if user is None:
        return err("Invalid email or password.", 401)
 
    user_logged_in.send(sender=user.__class__, request=request, user=user)  # records a LoginEvent
    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "username": user.username,
        "is_superuser": user.is_superuser,
    })
 
 
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response({"id": u.id, "username": u.username, "email": u.email})
 
 
# ---------- Houses ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def booking_cancel(request, pk):
    b = own_booking(request, pk)
    if b.status == "cancelled":
        return err("Already cancelled.")
    b.status = "cancelled"
    b.save()
    return Response(BookingSerializer(b).data)
 
 
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_periods(request, pk):
    periods = own_booking(request, pk).periods.all()
    return Response(PaymentPeriodSerializer(periods, many=True).data)
 
 
# ---------- Payments (mock M-Pesa) ----------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_mock(request, kind, pk):
    """Demo payment: pretends to be M-Pesa. kind is 'booking' or 'period'."""
    phone = re.sub(r"\D", "", request.data.get("phone", "") or "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not re.fullmatch(r"254\d{9}", phone):
        return err("Send a phone number like 0712345678.")
 
    if kind == "booking":
        target = own_booking(request, pk)
        if target.status != "confirmed" or target.is_long:
            return err("This booking can't be paid this way.")
        amount = target.total_price
    elif kind == "period":
        target = get_object_or_404(PaymentPeriod.objects.select_related("booking"),
                                   pk=pk, booking__user=request.user)
        if target.booking.status != "confirmed":
            return err("Cancelled bookings can't be paid.")
        amount = target.amount
    else:
        return err("Use 'booking' or 'period'.", 404)
 
    if target.paid:
        return err("Already paid.")
 
    target.paid, target.paid_at = True, timezone.now()
    target.save()
    receipt = "MOCK" + "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))
    return Response({"status": "success", "receipt": receipt,
                     "phone": phone, "amount": str(amount),
                     "message": f"KES {amount} received from {phone}"})
 
 
# ---------- Dashboard ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    due = PaymentPeriod.objects.filter(booking__user=request.user,
                                       booking__status="confirmed", paid=False).count()
    ann = [{"title": a.title, "message": a.message, "created_at": a.created_at}
           for a in Announcement.objects.all()[:5]]
    return Response({"payments_due": due, "announcements": ann})
 
 
# ---------- Superuser only ----------
@api_view(["GET"])
@permission_classes([IsSuperuser])
def user_list(request):
    users = get_user_model().objects.all().order_by("id")
    return Response([{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "is_superuser": u.is_superuser,
        "date_joined": u.date_joined,
        "bookings": Booking.objects.filter(user=u).count(),
    } for u in users])
 
 
@api_view(["GET"])
@permission_classes([IsSuperuser])
def user_detail(request, pk):
    u = get_object_or_404(get_user_model(), pk=pk)
    bookings = Booking.objects.filter(user=u).select_related("house").order_by("-check_in")
    return Response({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "bookings": BookingSerializer(bookings, many=True).data,
    })
 
