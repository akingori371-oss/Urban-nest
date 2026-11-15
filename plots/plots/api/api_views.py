
import re
import base64
import logging
import threading
import time
import requests

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal, InvalidOperation
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import (
    House, Booking, PaymentPeriod, Announcement, MpesaPayment, MpesaCallbackEvent
)

from .serializers import (
    RegisterSerializer, HouseSerializer,
    BookingSerializer, PaymentPeriodSerializer, HouseDetailSerializer
)

logger = logging.getLogger(__name__)
_oauth_cache_lock = threading.Lock()
_oauth_cached_token = None
_oauth_token_expires_at = 0.0
PAYMENT_QUERY_INTERVAL = 15


class DarajaRequestError(Exception):
    def __init__(self, stage, detail, outcome_uncertain=False, response=None):
        super().__init__(detail)
        self.stage = stage
        self.detail = detail
        self.outcome_uncertain = outcome_uncertain
        self.response = response if isinstance(response, dict) else {}
 
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
    profile = getattr(user, "manager_profile", None)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "username": user.username,
        "is_superuser": user.is_superuser,
        "is_manager": bool(user.is_superuser or profile),
        "is_main_manager": bool(user.is_superuser or (profile and profile.is_main)),
    })
 
 
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    profile = getattr(u, "manager_profile", None)
    return Response({"id": u.id, "username": u.username, "email": u.email,
                     "is_manager": bool(u.is_superuser or profile),
                     "is_main_manager": bool(u.is_superuser or (profile and profile.is_main))})
 
 
# ---------- Houses ----------
class HousePagination(PageNumberPagination):
    page_size = 20
    page_query_param = "page"


def validate_house_dates(request):
    raw_in = request.query_params.get("check_in")
    raw_out = request.query_params.get("check_out")
    if bool(raw_in) != bool(raw_out):
        return None, None, err("Send both check_in and check_out as YYYY-MM-DD.")
    if not raw_in:
        return None, None, None
    cin, cout = parse_date(raw_in), parse_date(raw_out)
    if cin is None or cout is None:
        return None, None, err("Dates must be YYYY-MM-DD.")
    if cout <= cin:
        return None, None, err("check_out must be after check_in.")
    return cin, cout, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def house_list(request):
    cin, cout, date_error = validate_house_dates(request)
    if date_error:
        return date_error
    qs = House.objects.filter(is_active=True).prefetch_related("photos").annotate(avg_rating=Avg("reviews__rating"),
                                review_count=Count("reviews"))
    if cin and cout:
        busy = Booking.objects.filter(status="confirmed", check_in__lt=cout,
                                      check_out__gt=cin).values_list("house_id", flat=True)
        qs = qs.exclude(id__in=busy)
    search = request.query_params.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(location__icontains=search)
                       | Q(description__icontains=search))
    ordering = request.query_params.get("ordering", "id")
    allowed_ordering = {"id", "name", "location", "bedrooms", "price_per_night"}
    if ordering.lstrip("-") not in allowed_ordering:
        return err("Unsupported ordering field.")
    qs = qs.order_by(ordering)
    paginator = HousePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(HouseSerializer(page, many=True, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def house_detail(request, pk):
    cin, cout, date_error = validate_house_dates(request)
    if date_error:
        return date_error
    house = get_object_or_404(House.objects.filter(is_active=True).prefetch_related("photos").annotate(
        avg_rating=Avg("reviews__rating"), review_count=Count("reviews")
    ).prefetch_related("reviews"), pk=pk)
    return Response(HouseDetailSerializer(house, context={"request": request}).data)

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
 
 
# ---------- Daraja payments ----------
def normalize_mpesa_phone(value):
    if not isinstance(value, str) or not re.fullmatch(r"\+?[\d\s().-]+", value.strip()):
        return None
    phone = re.sub(r"\D", "", value)
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    return phone if re.fullmatch(r"254[71]\d{8}", phone) else None


def payment_is_uncertain(payment):
    if payment.status == "uncertain" or (payment.status == "pending" and not payment.checkout_request_id):
        return True
    if payment.status != "failed" or payment.checkout_request_id:
        return False
    description = payment.result_description.lower()
    return not (
        description.startswith("oauth token retrieval")
        or description.startswith("stk push was rejected")
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_mock(request, kind, pk):
    if kind not in {"booking", "period"}:
        return err("Use 'booking' or 'period'.", 404)
    phone = normalize_mpesa_phone(request.data.get("phone", ""))
    if not phone:
        return err("Enter a valid Kenyan M-Pesa number, such as 0712345678.")

    with transaction.atomic():
        if kind == "booking":
            target = get_object_or_404(Booking.objects.select_for_update(), pk=pk, user=request.user)
            if target.status != "confirmed" or target.is_long:
                return err("This booking can't be paid this way.")
            if target.paid:
                return err("Already paid.")
            related = MpesaPayment.objects.filter(booking=target)
            booking, period, amount, reference = target, None, target.total_price, f"BOOKING-{target.pk}"
        elif kind == "period":
            target = get_object_or_404(PaymentPeriod.objects.select_for_update().select_related("booking"), pk=pk, booking__user=request.user)
            if target.booking.status != "confirmed":
                return err("Cancelled bookings can't be paid.")
            if target.paid:
                return err("Already paid.")
            related = MpesaPayment.objects.filter(period=target)
            booking, period, amount, reference = None, target, target.amount, f"PERIOD-{target.pk}"
        existing = related.filter(status__in=["pending", "uncertain"]).order_by("-created_at").first()
        if existing: return Response(payment_data(existing))
        legacy_uncertain = next(
            (attempt for attempt in related.filter(status="failed").order_by("-created_at")
             if payment_is_uncertain(attempt)),
            None,
        )
        if legacy_uncertain:
            return Response({
                "detail": "An earlier payment attempt has no checkout ID and cannot be confirmed. Its outcome must be reconciled before another payment is started.",
                "payment_id": legacy_uncertain.pk,
                "outcome_uncertain": True,
            }, status=409)
        amount = Decimal(amount)
        if amount <= 0 or amount != amount.to_integral_value():
            return err("The payment amount must be a positive whole number of Kenyan shillings.")
        if not settings.MPESA_CALLBACK_URL_VALID:
            logger.error("Daraja payment initiation blocked: callback URL configuration is invalid.")
            return Response({"detail": "M-Pesa callback URL must be a public HTTPS URL ending in /api/mpesa/callback/. Payment was not started.", "outcome_uncertain": False}, status=503)
        if not all((settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET,
                    settings.MPESA_SHORTCODE, settings.MPESA_PASSKEY)):
            logger.error("Daraja payment initiation blocked: sandbox configuration is incomplete.")
            return Response({"detail": "M-Pesa sandbox configuration is incomplete. Payment was not started.", "outcome_uncertain": False}, status=503)
        payment = MpesaPayment.objects.create(booking=booking, period=period, phone=phone, amount=amount)

    try:
        result = initiate_stk_push(phone, int(amount), reference)
        if not result.get("CheckoutRequestID") or not result.get("MerchantRequestID"):
            raise DarajaRequestError(
                "STK Push",
                "STK Push outcome uncertain: response omitted required request identifiers; do not retry until reconciled.",
                True,
                response=result,
            )
        payment.checkout_request_id = result["CheckoutRequestID"]
        payment.merchant_request_id = result["MerchantRequestID"]
        payment.stk_response = result
        payment.save(update_fields=["checkout_request_id", "merchant_request_id", "stk_response"])
    except DarajaRequestError as exc:
        payment.status = "uncertain" if exc.outcome_uncertain else "failed"
        payment.checkout_request_id = exc.response.get("CheckoutRequestID") or None
        payment.merchant_request_id = exc.response.get("MerchantRequestID") or ""
        payment.stk_response = exc.response
        payment.result_description = exc.detail[:255]
        payment.save(update_fields=[
            "status", "checkout_request_id", "merchant_request_id", "stk_response",
            "result_description",
        ])
        if exc.outcome_uncertain:
            return Response(payment_data(payment), status=202)
        logger.error("Daraja %s failed before an STK Push was accepted.", exc.stage)
        return Response({"detail": exc.detail, "outcome_uncertain": False}, status=502)
    event = MpesaCallbackEvent.objects.filter(checkout_request_id=payment.checkout_request_id, processed_at__isnull=True).first()
    if event:
        process_mpesa_callback(event.payload)
        payment.refresh_from_db()
    return Response(payment_data(payment), status=201)


def masked_phone(phone):
    return f"*******{phone[-4:]}" if phone else ""


def payment_data(payment):
    uncertain = payment_is_uncertain(payment)
    callback_event = None
    if payment.checkout_request_id:
        callback_event = MpesaCallbackEvent.objects.filter(
            checkout_request_id=payment.checkout_request_id,
            processed_at__isnull=True,
        ).only("payload").first()
    callback = {}
    if callback_event and isinstance(callback_event.payload, dict):
        body = callback_event.payload.get("Body")
        stk_callback = body.get("stkCallback") if isinstance(body, dict) else None
        if isinstance(stk_callback, dict):
            callback = stk_callback
    callback_code = callback.get("ResultCode")
    try:
        if isinstance(callback_code, bool):
            raise ValueError
        callback_code = int(callback_code) if callback_code is not None else None
    except (TypeError, ValueError):
        callback_code = None
    return {"id": payment.id, "status": "uncertain" if uncertain else payment.status,
            "booking": payment.booking_id,
            "period": payment.period_id, "amount": str(payment.amount), "phone": masked_phone(payment.phone),
            "receipt": payment.receipt or None, "result_code": payment.result_code,
            "result_description": payment.result_description,
            "initiation_uncertain": uncertain and not payment.checkout_request_id,
            "callback_reconciliation_pending": callback_event is not None,
            "callback_result_code": callback_code,
            "stk_accepted": bool(payment.checkout_request_id and payment.status == "pending")}


def queue_mpesa_callback(checkout_id, data):
    event, created = MpesaCallbackEvent.objects.get_or_create(
        checkout_request_id=checkout_id,
        defaults={"payload": data},
    )
    if not created and event.processed_at is None and event.payload != data:
        event.payload = data
        event.save(update_fields=["payload"])


def callback_metadata_values(callback):
    metadata = callback.get("CallbackMetadata")
    items = metadata.get("Item") if isinstance(metadata, dict) else None
    if not isinstance(items, list):
        return None
    return {
        item["Name"]: item.get("Value")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("Name"), str)
    }


def process_mpesa_callback(data, verified_result=None):
    if not isinstance(data, dict):
        return Response({"detail": "Invalid callback structure."}, status=400)
    body = data.get("Body")
    callback = body.get("stkCallback") if isinstance(body, dict) else None
    if not isinstance(callback, dict):
        return Response({"detail": "Invalid callback structure."}, status=400)
    checkout_id = callback.get("CheckoutRequestID")
    merchant_id = callback.get("MerchantRequestID")
    if not isinstance(checkout_id, str) or not checkout_id or len(checkout_id) > 100:
        return Response({"detail": "Missing or invalid checkout request ID."}, status=400)
    if not isinstance(merchant_id, str) or not merchant_id or len(merchant_id) > 100:
        return Response({"detail": "Missing or invalid merchant request ID."}, status=400)
    try:
        raw_code = callback.get("ResultCode")
        if isinstance(raw_code, bool):
            raise ValueError
        code = int(raw_code)
    except (ValueError, TypeError):
        return Response({"detail": "Invalid callback result code."}, status=400)
    result_description = callback.get("ResultDesc", "")
    if not isinstance(result_description, str):
        return Response({"detail": "Invalid callback result description."}, status=400)

    payment = MpesaPayment.objects.filter(checkout_request_id=checkout_id).first()
    if not payment:
        queue_mpesa_callback(checkout_id, data)
        return Response({"ResultCode": 0, "ResultDesc": "Queued for reconciliation"}, status=202)
    if payment.merchant_request_id and merchant_id != payment.merchant_request_id:
        return Response({"detail": "Merchant request ID mismatch."}, status=400)

    terminal_statuses = {"success", "failed", "cancelled", "review"}
    needs_late_receipt = payment.status == "success" and not payment.receipt and code == 0
    if payment.status in terminal_statuses and not needs_late_receipt:
        event, _ = MpesaCallbackEvent.objects.get_or_create(
            checkout_request_id=checkout_id,
            defaults={"payload": data, "processed_at": timezone.now()},
        )
        if event.processed_at is None:
            event.processed_at = timezone.now()
            event.save(update_fields=["processed_at"])
        return Response({"ResultCode": 0, "ResultDesc": "Already processed"})

    if verified_result is None:
        try:
            verified_result = query_stk_push(checkout_id)
        except DarajaRequestError as exc:
            logger.warning("Daraja callback for payment %s could not be verified (%s).", payment.pk, exc.stage)
            queue_mpesa_callback(checkout_id, data)
            return Response({"ResultCode": 0, "ResultDesc": "Awaiting Daraja reconciliation"}, status=202)

    try:
        verified_code = int(verified_result.get("ResultCode"))
        if isinstance(verified_result.get("ResultCode"), bool):
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        verified_code = None
    if (
        not isinstance(verified_result, dict)
        or str(verified_result.get("ResponseCode")) != "0"
        or verified_result.get("CheckoutRequestID") != checkout_id
        or (payment.merchant_request_id
            and verified_result.get("MerchantRequestID") != payment.merchant_request_id)
        or verified_code != code
    ):
        logger.warning("Daraja callback for payment %s did not match its verified query.", payment.pk)
        queue_mpesa_callback(checkout_id, data)
        return Response({"ResultCode": 0, "ResultDesc": "Awaiting Daraja reconciliation"}, status=202)

    with transaction.atomic():
        payment = MpesaPayment.objects.select_for_update().filter(checkout_request_id=checkout_id).first()
        if not payment:
            queue_mpesa_callback(checkout_id, data)
            return Response({"ResultCode": 0, "ResultDesc": "Queued for reconciliation"}, status=202)
        if payment.merchant_request_id and merchant_id != payment.merchant_request_id:
            return Response({"detail": "Merchant request ID mismatch."}, status=400)
        if not payment.merchant_request_id:
            payment.merchant_request_id = merchant_id
        payment.callback_data = callback
        payment.query_response = verified_result
        event = MpesaCallbackEvent.objects.filter(checkout_request_id=checkout_id).first()
        if payment.status in terminal_statuses:
            if payment.status == "success" and code == 0 and not payment.receipt:
                values = callback_metadata_values(callback)
                if values is None:
                    return Response({"detail": "Missing callback transaction details."}, status=400)
                try:
                    paid_amount = Decimal(str(values["Amount"]))
                    paid_phone = normalize_mpesa_phone(str(values["PhoneNumber"]))
                    receipt = values["MpesaReceiptNumber"]
                except (KeyError, InvalidOperation, ValueError, TypeError):
                    return Response({"detail": "Missing callback transaction details."}, status=400)
                if (paid_amount.is_finite() and paid_amount == payment.amount and paid_phone == payment.phone
                        and isinstance(receipt, str) and receipt.strip()):
                    payment.receipt = receipt.strip()[:50]
                    payment.callback_data = callback
                    payment.save(update_fields=["receipt", "callback_data", "query_response"])
            if event and event.processed_at is None:
                event.processed_at = timezone.now()
                event.save(update_fields=["processed_at"])
            return Response({"ResultCode": 0, "ResultDesc": "Already processed"})
        payment.result_code = code
        if code:
            payment.status = "cancelled" if code == 1032 else "failed"
            payment.result_description = result_description[:255] or "Payment did not complete."
        else:
            values = callback_metadata_values(callback)
            if values is None:
                return Response({"detail": "Missing callback transaction details."}, status=400)
            try:
                paid_amount = Decimal(str(values["Amount"]))
                paid_phone = normalize_mpesa_phone(str(values["PhoneNumber"]))
                receipt = values["MpesaReceiptNumber"]
            except (KeyError, InvalidOperation, ValueError, TypeError):
                return Response({"detail": "Missing callback transaction details."}, status=400)
            if (not paid_amount.is_finite() or paid_phone is None or paid_amount != payment.amount or paid_phone != payment.phone
                    or not isinstance(receipt, str) or not receipt.strip()):
                return Response({"detail": "Callback transaction details mismatch."}, status=400)
            target = payment.booking or payment.period.booking
            if target.status != "confirmed":
                payment.status = "review"
                payment.result_description = "Payment reported for a cancelled booking; manual reconciliation is required."
            else:
                payment.status = "success"; payment.receipt = receipt.strip()[:50]
                payment.result_description = ""
                payment.callback_data = callback
                now = timezone.now()
                obj = payment.booking or payment.period
                obj.paid = True; obj.paid_at = now; obj.save(update_fields=["paid", "paid_at"])
        payment.save()
        event, _ = MpesaCallbackEvent.objects.get_or_create(
            checkout_request_id=checkout_id,
            defaults={"payload": data},
        )
        if event.payload != data and event.processed_at is None:
            event.payload = data
        if event.processed_at is None:
            event.processed_at = timezone.now()
            event.save(update_fields=["payload", "processed_at"])
    logger.info("Daraja callback reconciled for payment %s with result code %s.", payment.pk, code)
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


@api_view(["POST"])
@permission_classes([AllowAny])
def mpesa_callback(request):
    return process_mpesa_callback(request.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_status(request, pk):
    payment = get_object_or_404(MpesaPayment.objects.filter(Q(booking__user=request.user) | Q(period__booking__user=request.user)), pk=pk)
    if payment.status in {"pending", "uncertain"} and payment.checkout_request_id:
        now = timezone.now()
        should_query = False
        query_result = None
        with transaction.atomic():
            locked = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
            last_query = locked.last_query_at
            if (locked.status in {"pending", "uncertain"} and locked.checkout_request_id
                    and (last_query is None or (now - last_query).total_seconds() >= PAYMENT_QUERY_INTERVAL)):
                locked.last_query_at = now
                locked.save(update_fields=["last_query_at"])
                should_query = True
        if should_query:
            try:
                query_result = query_stk_push(payment.checkout_request_id)
            except DarajaRequestError as exc:
                logger.warning("Daraja STK query failed for payment %s (%s).", payment.pk, exc.stage)
            else:
                apply_stk_query(payment.pk, query_result)
                event = MpesaCallbackEvent.objects.filter(
                    checkout_request_id=payment.checkout_request_id,
                    processed_at__isnull=True,
                ).first()
                if event:
                    process_mpesa_callback(event.payload, verified_result=query_result)
        payment.refresh_from_db()
    return Response(payment_data(payment))


def apply_stk_query(payment_id, data):
    if not isinstance(data, dict) or str(data.get("ResponseCode")) != "0":
        return
    with transaction.atomic():
        payment = MpesaPayment.objects.select_for_update().filter(pk=payment_id).first()
        if payment is None or payment.status not in {"pending", "uncertain"}:
            return
        if data.get("CheckoutRequestID") != payment.checkout_request_id:
            logger.warning("Daraja STK query returned a mismatched checkout ID for payment %s.", payment.pk)
            return
        merchant_id = data.get("MerchantRequestID")
        if payment.merchant_request_id and merchant_id != payment.merchant_request_id:
            logger.warning("Daraja STK query returned a mismatched merchant ID for payment %s.", payment.pk)
            return
        try:
            raw_code = data.get("ResultCode")
            if isinstance(raw_code, bool):
                raise ValueError
            result_code = int(raw_code)
        except (TypeError, ValueError):
            return
        payment.query_response = data
        payment.result_code = result_code
        description = data.get("ResultDesc", "")
        payment.result_description = description[:255] if isinstance(description, str) else ""
        if result_code == 0:
            target = payment.booking or payment.period.booking
            if target.status != "confirmed":
                payment.status = "review"
                payment.result_description = "Payment reported for a cancelled booking; manual reconciliation is required."
            else:
                payment.status = "success"
                now = timezone.now()
                obj = payment.booking or payment.period
                obj.paid = True
                obj.paid_at = now
                obj.save(update_fields=["paid", "paid_at"])
        else:
            payment.status = "cancelled" if result_code == 1032 else "failed"
            payment.result_description = payment.result_description or "Payment did not complete."
        payment.save(update_fields=[
            "status", "result_code", "result_description", "query_response",
        ])


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
           for a in Announcement.objects.filter(is_published=True).filter(Q(recipients__isnull=True) | Q(recipients=request.user)).distinct()[:5]]
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
    global _oauth_cached_token, _oauth_token_expires_at
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        logger.error("Daraja OAuth token retrieval blocked: sandbox credentials are not configured.")
        raise DarajaRequestError(
            "OAuth",
            "OAuth token retrieval failed: sandbox credentials are not configured; STK Push was not submitted.",
        )

    with _oauth_cache_lock:
        now = time.monotonic()
        if _oauth_cached_token and now < _oauth_token_expires_at:
            return _oauth_cached_token

        url = f"{settings.MPESA_API_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(
                url,
                auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
                timeout=(5, 15),
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout as exc:
            logger.warning("Daraja OAuth token retrieval timed out (%s).", type(exc).__name__)
            raise DarajaRequestError(
                "OAuth", f"OAuth token retrieval timed out ({type(exc).__name__}); STK Push was not submitted."
            ) from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            logger.warning("Daraja OAuth token retrieval returned HTTP %s.", status)
            raise DarajaRequestError(
                "OAuth", f"OAuth token retrieval failed with HTTP {status}; STK Push was not submitted."
            ) from exc
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Daraja OAuth token retrieval failed (%s).", type(exc).__name__)
            raise DarajaRequestError(
                "OAuth", f"OAuth token retrieval failed ({type(exc).__name__}); STK Push was not submitted."
            ) from exc

        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token.strip():
            logger.warning("Daraja OAuth token response did not contain a valid access token.")
            raise DarajaRequestError(
                "OAuth", "OAuth token retrieval returned an invalid response; STK Push was not submitted."
            )
        try:
            expires_in = int(data.get("expires_in", 0))
        except (TypeError, ValueError):
            expires_in = 0
        if expires_in > 60:
            _oauth_cached_token = token
            _oauth_token_expires_at = time.monotonic() + expires_in - 60
        return token


def _clear_mpesa_token_cache():
    global _oauth_cached_token, _oauth_token_expires_at
    with _oauth_cache_lock:
        _oauth_cached_token = None
        _oauth_token_expires_at = 0.0


def initiate_stk_push(phone, amount, reference):
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        f"{shortcode}{passkey}{timestamp}".encode()
    ).decode()

    token = mpesa_access_token()

    url = f"{settings.MPESA_API_BASE_URL}/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": settings.MPESA_TRANSACTION_TYPE,
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": reference,
        "TransactionDesc": "Urban Nest Payment"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=(5, 30)
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        logger.warning("Daraja STK Push submission timed out (%s); outcome is uncertain.", type(exc).__name__)
        raise DarajaRequestError(
            "STK Push",
            f"STK Push outcome uncertain after {type(exc).__name__}; do not retry until this attempt is reconciled.",
            True,
        ) from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        uncertain = status is None or status >= 500
        logger.warning("Daraja STK Push submission returned HTTP %s (outcome uncertain: %s).", status or "unknown", uncertain)
        detail = (f"STK Push outcome uncertain after HTTP {status}; do not retry until this attempt is reconciled."
                  if uncertain else f"STK Push was rejected with HTTP {status}.")
        raise DarajaRequestError("STK Push", detail, uncertain) from exc
    except requests.RequestException as exc:
        logger.warning("Daraja STK Push submission failed (%s); outcome is uncertain.", type(exc).__name__)
        raise DarajaRequestError(
            "STK Push",
            f"STK Push outcome uncertain after {type(exc).__name__}; do not retry until this attempt is reconciled.",
            True,
        ) from exc

    try:
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Daraja STK Push returned an unreadable response (%s); outcome is uncertain.", type(exc).__name__)
        raise DarajaRequestError(
            "STK Push",
            "STK Push outcome uncertain: Daraja response could not be read; do not retry until reconciled.",
            True,
        ) from exc
    if not isinstance(data, dict):
        logger.warning("Daraja STK Push returned an unexpected response; outcome is uncertain.")
        raise DarajaRequestError(
            "STK Push",
            "STK Push outcome uncertain: Daraja response was invalid; do not retry until reconciled.",
            True,
        )

    response_code = data.get("ResponseCode")
    if str(response_code) != "0":
        if response_code is None:
            logger.warning("Daraja STK Push response omitted ResponseCode; outcome is uncertain.")
            raise DarajaRequestError(
                "STK Push",
                "STK Push outcome uncertain: response omitted ResponseCode; do not retry until reconciled.",
                True,
                response=data,
            )
        safe_code = str(response_code)[:20]
        logger.warning("Daraja rejected STK Push (ResponseCode=%s).", safe_code)
        raise DarajaRequestError(
            "STK Push",
            "STK Push was rejected by Daraja (ResponseCode {}).".format(safe_code),
            response=data,
        )
    if not data.get("CheckoutRequestID"):
        logger.warning("Daraja STK Push response omitted CheckoutRequestID; outcome is uncertain.")
        raise DarajaRequestError(
            "STK Push",
            "STK Push outcome uncertain: CheckoutRequestID was missing; do not retry until reconciled.",
            True,
            response=data,
        )
    if not data.get("MerchantRequestID"):
        logger.warning("Daraja STK Push response omitted MerchantRequestID; outcome is uncertain.")
        raise DarajaRequestError(
            "STK Push",
            "STK Push outcome uncertain: MerchantRequestID was missing; do not retry until reconciled.",
            True,
            response=data,
        )
    return data


def query_stk_push(checkout_request_id):
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    if not isinstance(checkout_request_id, str) or not checkout_request_id:
        raise DarajaRequestError("STK query", "A CheckoutRequestID is required for a Daraja status query.")
    if not shortcode or not passkey:
        raise DarajaRequestError("STK query", "Daraja status query configuration is incomplete.")
    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{shortcode}{passkey}{timestamp}".encode()
    ).decode()
    token = mpesa_access_token()
    url = f"{settings.MPESA_API_BASE_URL}/mpesa/stkpushquery/v1/query"
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=(5, 30),
        )
        response.raise_for_status()
        data = response.json()
    except requests.Timeout as exc:
        logger.warning("Daraja STK query timed out (%s).", type(exc).__name__)
        raise DarajaRequestError("STK query", "Daraja payment status could not be checked.") from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning("Daraja STK query returned HTTP %s.", status)
        raise DarajaRequestError("STK query", f"Daraja payment status query failed with HTTP {status}.") from exc
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Daraja STK query failed (%s).", type(exc).__name__)
        raise DarajaRequestError("STK query", "Daraja payment status could not be checked.") from exc

    if not isinstance(data, dict):
        logger.warning("Daraja STK query returned an invalid response.")
        raise DarajaRequestError("STK query", "Daraja payment status returned an invalid response.")
    return data
