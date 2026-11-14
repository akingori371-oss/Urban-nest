import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..manager_permissions import IsManager, IsMainManager
from ..models import (Announcement, Booking, House, HousePhoto, ManagerInvitation,
                      ManagerProfile, MpesaPayment, PaymentPeriod)
from .serializers import (BookingSerializer, HousePhotoSerializer,
                          ManagerAnnouncementSerializer, ManagerHouseSerializer,
                          ManagerInvitationSerializer, ManagerPaymentSerializer)

User = get_user_model()
MAIN_MANAGER_EMAIL = "akingori371@gmail.com"
MAX_PHOTO_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _valid_image_file(upload):
    header = upload.read(12)
    upload.seek(0)
    return (
        (upload.content_type == "image/jpeg" and header.startswith(b"\xff\xd8\xff"))
        or (upload.content_type == "image/png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
        or (upload.content_type == "image/webp" and header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )


class ManagerPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def paginated(request, queryset, serializer, *, context=None):
    paginator = ManagerPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(serializer(page, many=True, context=context).data)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_dashboard(request):
    today = timezone.localdate()
    active_houses = House.objects.filter(is_active=True)
    occupied_ids = Booking.objects.filter(status="confirmed", check_in__lte=today,
                                          check_out__gt=today).values("house_id").distinct()
    payments = MpesaPayment.objects.all()
    long_outstanding = PaymentPeriod.objects.filter(booking__status="confirmed", paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    short_outstanding = Booking.objects.filter(status="confirmed", paid=False,
        check_out__lte=F("check_in") + timedelta(days=30)).aggregate(total=Sum("total_price"))["total"] or Decimal("0")
    tenants = User.objects.filter(manager_profile__isnull=True, is_superuser=False)
    return Response({
        "apartments_total": House.objects.count(),
        "apartments_available": active_houses.exclude(pk__in=occupied_ids).count(),
        "apartments_occupied": active_houses.filter(pk__in=occupied_ids).count(),
        "tenants_total": tenants.count(),
        "bookings_total": Booking.objects.count(),
        "bookings_pending": Booking.objects.filter(status="pending").count(),
        "bookings_confirmed": Booking.objects.filter(status="confirmed").count(),
        "bookings_cancelled": Booking.objects.filter(status="cancelled").count(),
        "payments_success": payments.filter(status="success").count(),
        "payments_pending_review": payments.filter(status__in=["pending", "review"]).count(),
        "payments_failed": payments.filter(status="failed").count(),
        "outstanding_balance": str(short_outstanding + long_outstanding),
        "recent_bookings": list(Booking.objects.select_related("house", "user").order_by("-created_at").values("id", "house__name", "user__username", "check_in", "check_out", "status", "total_price", "created_at")[:8]),
        "recent_payments": list(payments.select_related("booking__house", "booking__user", "period__booking__house", "period__booking__user").order_by("-created_at").values("id", "status", "amount", "phone", "receipt", "created_at", "booking__house__name", "period__booking__house__name")[:8]),
        "recent_tenants": list(tenants.order_by("-date_joined").values("id", "username", "email", "date_joined")[:8]),
        "recent_announcements": list(Announcement.objects.order_by("-created_at").values("id", "title", "is_published", "created_at")[:8]),
    })


@api_view(["GET", "POST"])
@permission_classes([IsManager])
def manager_houses(request):
    if request.method == "POST":
        serializer = ManagerHouseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        house = serializer.save()
        return Response(ManagerHouseSerializer(house).data, status=201)
    queryset = House.objects.all().order_by("id")
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(location__icontains=search))
    active = request.query_params.get("active")
    if active in {"true", "false"}:
        queryset = queryset.filter(is_active=(active == "true"))
    return paginated(request, queryset, ManagerHouseSerializer)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsManager])
def manager_house_detail(request, pk):
    house = get_object_or_404(House, pk=pk)
    if request.method == "GET":
        data = ManagerHouseSerializer(house).data
        data["photos"] = HousePhotoSerializer(house.photos.all(), many=True, context={"request": request}).data
        data["bookings"] = BookingSerializer(house.booking_set.select_related("user").order_by("-created_at")[:20], many=True).data
        return Response(data)
    if request.method == "DELETE":
        # Preserve booking/payment history by deactivating instead of deleting.
        house.is_active = False
        house.save(update_fields=["is_active"])
        return Response({"detail": "Apartment deactivated."})
    serializer = ManagerHouseSerializer(house, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsManager])
def manager_house_photos(request, pk):
    house = get_object_or_404(House, pk=pk)
    upload = request.FILES.get("image")
    if upload is None:
        return Response({"detail": "Select an image file."}, status=400)
    if upload.size > MAX_PHOTO_BYTES:
        return Response({"detail": "Images must be 8 MB or smaller."}, status=400)
    if upload.content_type not in ALLOWED_IMAGE_TYPES:
        return Response({"detail": "Use a JPEG, PNG, or WebP image."}, status=400)
    if not _valid_image_file(upload):
        return Response({"detail": "The uploaded file is not a valid JPEG, PNG, or WebP image."}, status=400)
    photo = HousePhoto.objects.create(house=house, image=upload, caption=request.data.get("caption", ""))
    return Response(HousePhotoSerializer(photo, context={"request": request}).data, status=201)


@api_view(["PUT", "DELETE"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsManager])
def manager_house_photo_detail(request, pk, photo_pk):
    photo = get_object_or_404(HousePhoto, pk=photo_pk, house_id=pk)
    if request.method == "PUT":
        upload = request.FILES.get("image")
        if upload is None or upload.size > MAX_PHOTO_BYTES or upload.content_type not in ALLOWED_IMAGE_TYPES:
            return Response({"detail": "Select a JPEG, PNG, or WebP image no larger than 8 MB."}, status=400)
        if not _valid_image_file(upload):
            return Response({"detail": "The uploaded file is not a valid image."}, status=400)
        photo.image.delete(save=False)
        photo.image = upload
        photo.caption = request.data.get("caption", photo.caption)
        photo.save()
        return Response(HousePhotoSerializer(photo, context={"request": request}).data)
    photo.image.delete(save=False)
    photo.delete()
    return Response(status=204)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_bookings(request):
    queryset = Booking.objects.select_related("house", "user").prefetch_related("periods").order_by("-created_at")
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(user__username__icontains=search) | Q(user__email__icontains=search) | Q(house__name__icontains=search) | Q(pk__icontains=search))
    for key, field in (("status", "status"), ("apartment", "house_id"), ("tenant", "user_id")):
        if request.query_params.get(key):
            queryset = queryset.filter(**{field: request.query_params[key]})
    for key in ("check_in_from", "check_in_to"):
        if request.query_params.get(key):
            date = parse_date(request.query_params[key])
            if not date:
                return Response({"detail": f"{key} must be YYYY-MM-DD."}, status=400)
            queryset = queryset.filter(**{"check_in__gte" if key.endswith("from") else "check_in__lte": date})
    paginator = ManagerPagination()
    page = paginator.paginate_queryset(queryset, request)
    results = BookingSerializer(page, many=True).data
    for item, booking in zip(results, page):
        item["tenant"] = {"id": booking.user_id, "username": booking.user.username, "email": booking.user.email}
        item["apartment"] = {"id": booking.house_id, "name": booking.house.name}
        item["payment_status"] = "paid" if (booking.paid if not booking.is_long else all(period.paid for period in booking.periods.all())) else "outstanding"
    return paginator.get_paginated_response(results)


@api_view(["GET", "POST"])
@permission_classes([IsManager])
def manager_booking_detail(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("house", "user").prefetch_related("periods"), pk=pk)
    if request.method == "GET":
        data = BookingSerializer(booking).data
        data.update({"tenant": {"id": booking.user_id, "username": booking.user.username, "email": booking.user.email},
                    "apartment": {"id": booking.house_id, "name": booking.house.name, "location": booking.house.location},
                    "periods": list(booking.periods.values("id", "number", "start", "end", "amount", "paid")),
                    "payments": list(MpesaPayment.objects.filter(Q(booking=booking) | Q(period__booking=booking)).values("id", "status", "amount", "phone", "receipt", "created_at"))})
        return Response(data)
    if request.data.get("status") != "cancelled" or booking.status != "confirmed":
        return Response({"detail": "Only confirmed bookings can be cancelled."}, status=400)
    with transaction.atomic():
        booking.status = "cancelled"
        booking.save(update_fields=["status"])
    return Response(BookingSerializer(booking).data)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_payments(request):
    queryset = MpesaPayment.objects.select_related("booking__house", "booking__user", "period__booking__house", "period__booking__user").order_by("-created_at")
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(phone__icontains=search) | Q(receipt__icontains=search) | Q(booking__user__username__icontains=search) | Q(booking__user__email__icontains=search) | Q(period__booking__user__username__icontains=search) | Q(period__booking__user__email__icontains=search))
    if request.query_params.get("status"):
        queryset = queryset.filter(status=request.query_params["status"])
    if request.query_params.get("tenant"):
        queryset = queryset.filter(Q(booking__user_id=request.query_params["tenant"]) | Q(period__booking__user_id=request.query_params["tenant"]))
    if request.query_params.get("apartment"):
        queryset = queryset.filter(Q(booking__house_id=request.query_params["apartment"]) | Q(period__booking__house_id=request.query_params["apartment"]))
    if request.query_params.get("date_from"):
        date_from = parse_date(request.query_params["date_from"])
        if not date_from:
            return Response({"detail": "date_from must be YYYY-MM-DD."}, status=400)
        queryset = queryset.filter(created_at__date__gte=date_from)
    if request.query_params.get("date_to"):
        date_to = parse_date(request.query_params["date_to"])
        if not date_to:
            return Response({"detail": "date_to must be YYYY-MM-DD."}, status=400)
        queryset = queryset.filter(created_at__date__lte=date_to)
    return paginated(request, queryset, ManagerPaymentSerializer)


@api_view(["GET", "POST"])
@permission_classes([IsManager])
def manager_announcements(request):
    if request.method == "POST":
        serializer = ManagerAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = serializer.save()
        return Response(ManagerAnnouncementSerializer(announcement).data, status=201)
    queryset = Announcement.objects.prefetch_related("recipients").order_by("-created_at")
    if request.query_params.get("published") in {"true", "false"}:
        queryset = queryset.filter(is_published=request.query_params["published"] == "true")
    return paginated(request, queryset, ManagerAnnouncementSerializer)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsManager])
def manager_announcement_detail(request, pk):
    announcement = get_object_or_404(Announcement.objects.prefetch_related("recipients"), pk=pk)
    if request.method == "DELETE":
        announcement.delete()
        return Response(status=204)
    serializer = ManagerAnnouncementSerializer(announcement, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_tenants(request):
    queryset = User.objects.filter(manager_profile__isnull=True, is_superuser=False).order_by("-date_joined")
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(username__icontains=search) | Q(email__icontains=search))
    if request.query_params.get("active") in {"true", "false"}:
        queryset = queryset.filter(is_active=request.query_params["active"] == "true")
    paginator = ManagerPagination()
    page = paginator.paginate_queryset(queryset, request)
    user_ids = [user.pk for user in page]
    booking_totals = {
        row["user_id"]: row
        for row in Booking.objects.filter(user_id__in=user_ids).values("user_id").annotate(
            total=Count("id"),
            short_due=Sum("total_price", filter=Q(status="confirmed", paid=False,
                check_out__lte=F("check_in") + timedelta(days=30))),
        )
    }
    period_totals = {
        row["booking__user_id"]: row["total"]
        for row in PaymentPeriod.objects.filter(booking__user_id__in=user_ids,
            booking__status="confirmed", paid=False).values("booking__user_id").annotate(total=Sum("amount"))
    }
    results = []
    for user in page:
        booking_summary = booking_totals.get(user.pk, {})
        short_due = booking_summary.get("short_due") or Decimal("0")
        period_due = period_totals.get(user.pk) or Decimal("0")
        results.append({"id": user.id, "username": user.username, "email": user.email, "date_joined": user.date_joined, "is_active": user.is_active, "bookings_count": booking_summary.get("total", 0), "outstanding_balance": str(short_due + period_due)})
    return paginator.get_paginated_response(results)


@api_view(["GET", "PATCH"])
@permission_classes([IsManager])
def manager_tenant_detail(request, pk):
    user = get_object_or_404(User, pk=pk, manager_profile__isnull=True, is_superuser=False)
    if request.method == "PATCH":
        if "is_active" not in request.data or not isinstance(request.data["is_active"], bool):
            return Response({"detail": "Provide is_active as true or false."}, status=400)
        user.is_active = request.data["is_active"]
        user.save(update_fields=["is_active"])
    bookings = Booking.objects.filter(user=user).select_related("house").order_by("-created_at")
    payments = MpesaPayment.objects.filter(Q(booking__user=user) | Q(period__booking__user=user)).order_by("-created_at")
    return Response({"id": user.id, "username": user.username, "email": user.email, "date_joined": user.date_joined, "is_active": user.is_active,
                     "bookings": list(bookings.values("id", "house__name", "check_in", "check_out", "total_price", "status", "paid")),
                     "payments": list(payments.values("id", "status", "amount", "phone", "receipt", "created_at"))})


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_invitation(invitation, token):
    base = getattr(settings, "URBAN_NEST_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    link = f"{base}/manager/invitations/accept/{token}"
    send_mail("Urban Nest manager invitation", f"Accept your manager invitation: {link}\nThis invitation expires in 7 days.", settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=False)


@api_view(["GET", "POST"])
@permission_classes([IsMainManager])
def manager_invitations(request):
    if request.method == "POST":
        mail_backend = settings.MAILERS.get("default", {}).get("BACKEND", "")
        if mail_backend.endswith("console.EmailBackend"):
            return Response({"detail": "Manager invitations are unavailable until a delivery email backend is configured."}, status=503)
        email = (request.data.get("email") or "").strip().lower()
        if not email or email == MAIN_MANAGER_EMAIL:
            return Response({"detail": "Enter a valid invited-manager email."}, status=400)
        if ManagerProfile.objects.filter(user__email__iexact=email).exists():
            return Response({"detail": "That person is already a manager."}, status=409)
        if ManagerInvitation.objects.filter(email__iexact=email, status="pending", expires_at__gt=timezone.now()).exists():
            return Response({"detail": "A pending invitation already exists."}, status=409)
        token = secrets.token_urlsafe(48)
        invitation = ManagerInvitation.objects.create(email=email, token_hash=_token_hash(token), invited_by=request.user, expires_at=timezone.now() + timedelta(days=7))
        try:
            _send_invitation(invitation, token)
        except Exception:
            invitation.delete()
            return Response({"detail": "Invitation email could not be sent."}, status=503)
        return Response({"id": invitation.id, "email": invitation.email, "status": invitation.status, "expires_at": invitation.expires_at}, status=201)
    queryset = ManagerInvitation.objects.select_related("invited_by").order_by("-created_at")
    return paginated(request, queryset, ManagerInvitationSerializer)


@api_view(["DELETE"])
@permission_classes([IsMainManager])
def manager_invitation_cancel(request, pk):
    invitation = get_object_or_404(ManagerInvitation, pk=pk, status="pending")
    invitation.status = "cancelled"
    invitation.token_hash = secrets.token_hex(32)
    invitation.save(update_fields=["status", "token_hash"])
    return Response(status=204)


@api_view(["GET"])
@permission_classes([IsMainManager])
def manager_list(request):
    profiles = ManagerProfile.objects.select_related("user").order_by("-is_main", "created_at")
    return Response([{"id": p.id, "user_id": p.user_id, "email": p.user.email, "username": p.user.username, "is_main": p.is_main, "created_at": p.created_at} for p in profiles])


@api_view(["DELETE"])
@permission_classes([IsMainManager])
def manager_remove(request, pk):
    profile = get_object_or_404(ManagerProfile.objects.select_related("user"), pk=pk, is_main=False)
    profile.delete()
    return Response(status=204)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_manager_invitation(request, token):
    if not request.user.email:
        return Response({"detail": "The authenticated account needs an email address."}, status=403)
    digest = _token_hash(token)
    with transaction.atomic():
        invitation = get_object_or_404(ManagerInvitation.objects.select_for_update(), token_hash=digest, status="pending")
        if invitation.expires_at <= timezone.now():
            invitation.status = "expired"
            invitation.save(update_fields=["status"])
            return Response({"detail": "This invitation has expired."}, status=410)
        if request.user.email.casefold() != invitation.email.casefold():
            return Response({"detail": "Sign in with the email address that received this invitation."}, status=403)
        if invitation.is_main_provision and invitation.email.casefold() != MAIN_MANAGER_EMAIL:
            return Response({"detail": "Main manager invitation configuration mismatch."}, status=400)
        if invitation.is_main_provision and ManagerProfile.objects.filter(is_main=True).exists():
            return Response({"detail": "A main manager is already configured."}, status=409)
        ManagerProfile.objects.update_or_create(user=request.user, defaults={"is_main": invitation.is_main_provision})
        invitation.status = "accepted"
        invitation.accepted_at = timezone.now()
        invitation.token_hash = secrets.token_hex(32)
        invitation.save(update_fields=["status", "accepted_at", "token_hash"])
    return Response({"detail": "Manager invitation accepted.", "is_main": invitation.is_main_provision})
