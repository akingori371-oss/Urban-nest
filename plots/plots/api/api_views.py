
import random
import re
import base64
import requests

from datetime import datetime
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal, ROUND_HALF_UP
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import (
    House, Booking, PaymentPeriod, Announcement, MpesaPayment, MpesaCallbackEvent
)

from .serializers import (
    RegisterSerializer, HouseSerializer,
    BookingSerializer, PaymentPeriodSerializer
)
 
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
    with transaction.atomic():
        house = House.objects.select_for_update().get(pk=d["house"].pk)
        if not house.is_free(d["check_in"], d["check_out"]):
            return err("That apartment is already booked for those dates.")
        total = (d["check_out"] - d["check_in"]).days * house.price_per_night
        booking = s.save(user=request.user, house=house, total_price=total)
        if booking.is_long:
            booking.create_periods()
    return Response(BookingSerializer(booking).data, status=201)
 
 
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def booking_cancel(request, pk):
    with transaction.atomic():
        b = get_object_or_404(Booking.objects.select_for_update(), pk=pk, user=request.user)
        if b.status == "cancelled": return err("Already cancelled.")
        paid = b.paid if not b.is_long else b.periods.filter(paid=True).exists()
        if paid: return err("This booking has been paid and cannot be cancelled because refunds are not supported.", 409)
        if b.mpesa_payments.filter(status="pending").exists():
            return err("A payment is pending. Wait for its result before cancelling.", 409)
        b.status = "cancelled"; b.save(update_fields=["status"])
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
    phone = re.sub(r"\D", "", request.data.get("phone", "") or "")
    if phone.startswith("0"): phone = "254" + phone[1:]
    if not re.fullmatch(r"254\d{9}", phone): return err("Send a phone number like 0712345678.")
    with transaction.atomic():
        if kind == "booking":
            target = get_object_or_404(Booking.objects.select_for_update(), pk=pk, user=request.user)
            if target.status != "confirmed" or target.is_long: return err("This booking can't be paid this way.")
            if target.paid: return err("Already paid.")
            related = MpesaPayment.objects.filter(booking=target)
            booking, period, amount, reference = target, None, target.total_price, f"BOOKING-{target.pk}"
        elif kind == "period":
            target = get_object_or_404(PaymentPeriod.objects.select_for_update().select_related("booking"), pk=pk, booking__user=request.user)
            if target.booking.status != "confirmed": return err("Cancelled bookings can't be paid.")
            if target.paid: return err("Already paid.")
            related = MpesaPayment.objects.filter(period=target)
            booking, period, amount, reference = None, target, target.amount, f"PERIOD-{target.pk}"
        else: return err("Use 'booking' or 'period'.", 404)
        existing = related.filter(status="pending").order_by("-created_at").first()
        if existing: return Response(payment_data(existing))
        amount = int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if amount <= 0: return err("Invalid payment amount.")
        payment = MpesaPayment.objects.create(booking=booking, period=period, phone=phone, amount=amount)
    try:
        result = initiate_stk_push(phone, amount, reference)
        if result.get("ResponseCode") != "0" or not result.get("CheckoutRequestID"):
            raise ValueError(result.get("ResponseDescription", "M-Pesa rejected the request."))
        payment.checkout_request_id = result["CheckoutRequestID"]
        payment.merchant_request_id = result.get("MerchantRequestID", "")
        payment.save(update_fields=["checkout_request_id", "merchant_request_id"])
    except (requests.RequestException, KeyError, ValueError) as exc:
        payment.status = "failed"; payment.result_description = str(exc)[:255]
        payment.save(update_fields=["status", "result_description"])
        return err("Could not start M-Pesa payment. Please retry.", 502)
    event = MpesaCallbackEvent.objects.filter(checkout_request_id=payment.checkout_request_id, processed_at__isnull=True).first()
    if event:
        process_mpesa_callback(event.payload)
        payment.refresh_from_db()
    return Response(payment_data(payment), status=201)


def payment_data(payment):
    return {"id": payment.id, "status": payment.status, "booking": payment.booking_id,
            "period": payment.period_id, "amount": str(payment.amount), "phone": payment.phone,
            "receipt": payment.receipt or None, "result_code": payment.result_code,
            "result_description": payment.result_description}


def process_mpesa_callback(data):
    callback = data.get("Body", {}).get("stkCallback", {}) if isinstance(data, dict) else {}
    checkout_id = callback.get("CheckoutRequestID")
    if not checkout_id: return Response({"message": "Missing checkout request ID"}, status=400)
    with transaction.atomic():
        payment = MpesaPayment.objects.select_for_update().filter(checkout_request_id=checkout_id).first()
        if not payment:
            MpesaCallbackEvent.objects.get_or_create(checkout_request_id=checkout_id, defaults={"payload": data})
            return Response({"ResultCode": 0, "ResultDesc": "Queued for reconciliation"}, status=202)
        merchant_id = callback.get("MerchantRequestID")
        if merchant_id and payment.merchant_request_id and merchant_id != payment.merchant_request_id:
            return Response({"message": "Merchant request ID mismatch"}, status=400)
        try: code = int(callback.get("ResultCode"))
        except (ValueError, TypeError): return Response({"message": "Invalid result code"}, status=400)
        event = MpesaCallbackEvent.objects.filter(checkout_request_id=checkout_id).first()
        if payment.status == "success":
            if event: event.processed_at = timezone.now(); event.save(update_fields=["processed_at"])
            return Response({"ResultCode": 0, "ResultDesc": "Already processed"})
        payment.result_code = code
        if code:
            payment.status = "failed"; payment.result_description = callback.get("ResultDesc", "Payment failed")[:255]
        else:
            items = callback.get("CallbackMetadata", {}).get("Item", [])
            values = {item.get("Name"): item.get("Value") for item in items if isinstance(item, dict)}
            try:
                paid_amount = Decimal(str(values["Amount"]))
                paid_phone = re.sub(r"\D", "", str(values["PhoneNumber"]))
                receipt = str(values["MpesaReceiptNumber"])
            except (KeyError, ValueError, TypeError): return Response({"message": "Missing callback transaction details"}, status=400)
            if paid_amount != payment.amount or paid_phone != payment.phone or not receipt:
                return Response({"message": "Callback transaction details mismatch"}, status=400)
            target = payment.booking or payment.period.booking
            if target.status != "confirmed":
                payment.status = "review"; payment.result_description = "Payment reported for cancelled booking; manual reconciliation required."
            else:
                payment.status = "success"; payment.receipt = receipt[:50]
                now = timezone.now()
                obj = payment.booking or payment.period
                obj.paid = True; obj.paid_at = now; obj.save(update_fields=["paid", "paid_at"])
        payment.save()
        if event: event.processed_at = timezone.now(); event.save(update_fields=["processed_at"])
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


@api_view(["POST"])
@permission_classes([AllowAny])
def mpesa_callback(request):
    return process_mpesa_callback(request.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_status(request, pk):
    payment = get_object_or_404(MpesaPayment.objects.filter(Q(booking__user=request.user) | Q(period__booking__user=request.user)), pk=pk)
    return Response(payment_data(payment))


# ---------- Dashboard ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    unpaid = PaymentPeriod.objects.filter(booking__user=request.user,
                                          booking__status="confirmed", paid=False)
    today = timezone.localdate()
    overdue = unpaid.filter(start__lt=today).count()
    due_now = unpaid.filter(start=today).count()
    future = unpaid.filter(start__gt=today).count()
    ann = [{"title": a.title, "message": a.message, "created_at": a.created_at}
           for a in Announcement.objects.all()[:5]]
    return Response({"payments_due": overdue + due_now, "payments_overdue": overdue,
                     "payments_due_now": due_now, "payments_future": future,
                     "announcements": ann})
 
 
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
 
def mpesa_access_token():
    url = f"{settings.MPESA_API_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET
        ),
        timeout=30
    )

    response.raise_for_status()

    return response.json()["access_token"]

def initiate_stk_push(phone, amount, reference):
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        f"{shortcode}{passkey}{timestamp}".encode()
    ).decode()

    token = mpesa_access_token()

    url = f"{settings.MPESA_API_BASE_URL}/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": reference,
        "TransactionDesc": "Urban Nest Payment"
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )

    response.raise_for_status()

    return response.json()    