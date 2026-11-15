import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..manager_permissions import IsManager, IsMainManager
from ..models import (Announcement, Booking, BookingNotification, House, HousePhoto, ManagerInvitation,
                      ManagerProfile)
from ..booking_notifications import (create_clarification_notification, create_decision_notification,
                                     mark_manager_request_read, send_booking_email)
from .serializers import (BookingSerializer, HousePhotoSerializer,
                          BookingClarificationSerializer, ManagerAnnouncementSerializer, ManagerHouseSerializer,
                          ManagerInvitationSerializer)

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
    tenants = User.objects.filter(manager_profile__isnull=True, is_superuser=False)
    return Response({
        "apartments_total": House.objects.count(),
        "apartments_available": active_houses.exclude(pk__in=occupied_ids).count(),
        "apartments_occupied": active_houses.filter(pk__in=occupied_ids).count(),
        "tenants_total": tenants.count(),
        "bookings_total": Booking.objects.count(),
        "bookings_pending": Booking.objects.filter(status="pending").count(),
        "bookings_confirmed": Booking.objects.filter(status="confirmed").count(),
        "bookings_rejected": Booking.objects.filter(status="rejected").count(),
        "bookings_cancelled": Booking.objects.filter(status="cancelled").count(),
        "unread_booking_requests": BookingNotification.objects.filter(
            user=request.user, kind="manager_booking_request", read_at__isnull=True).count(),
        "recent_bookings": list(Booking.objects.select_related("house", "user").order_by("-created_at").values(
            "id", "house__name", "user__username", "check_in", "check_out", "status", "total_price", "created_at")[:8]),
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
        # Preserve booking history by deactivating instead of deleting.
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
    queryset = Booking.objects.select_related("house", "user").order_by("-created_at")
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(user__username__icontains=search) | Q(user__email__icontains=search)
                                   | Q(house__name__icontains=search) | Q(pk__icontains=search))
    for key, field in (("status", "status"), ("apartment", "house_id"), ("tenant", "user_id")):
        if request.query_params.get(key):
            queryset = queryset.filter(**{field: request.query_params[key]})
    paginator = ManagerPagination()
    page = paginator.paginate_queryset(queryset, request)
    results = BookingSerializer(page, many=True).data
    read_booking_ids = set(BookingNotification.objects.filter(
        user=request.user, kind="manager_booking_request", read_at__isnull=False,
        booking_id__in=[booking.pk for booking in page],
    ).values_list("booking_id", flat=True))
    for item, booking in zip(results, page):
        item["tenant"] = {"id": booking.user_id, "username": booking.user.username,
                          "email": booking.user.email}
        item["apartment"] = {"id": booking.house_id, "name": booking.house.name}
        item["unread"] = booking.pk not in read_booking_ids
    return paginator.get_paginated_response(results)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_booking_unread_count(request):
    count = BookingNotification.objects.filter(
        user=request.user, kind="manager_booking_request", read_at__isnull=True).count()
    return Response({"unread_count": count})


@api_view(["GET"])
@permission_classes([IsManager])
def manager_booking_detail(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("house", "user"), pk=pk)
    mark_manager_request_read(request.user, booking)
    data = BookingSerializer(booking).data
    data.update({"tenant": {"id": booking.user_id, "username": booking.user.username,
                            "email": booking.user.email},
                 "apartment": {"id": booking.house_id, "name": booking.house.name,
                               "location": booking.house.location},
                 "clarification_requested": BookingNotification.objects.filter(
                     user=booking.user, booking=booking, kind="booking_clarification").exists(),
                 "unread": False})
    return Response(data)


def decide_booking(request, pk, decision):
    with transaction.atomic():
        candidate = get_object_or_404(Booking.objects.only("house_id"), pk=pk)
        House.objects.select_for_update().get(pk=candidate.house_id)
        booking = get_object_or_404(Booking.objects.select_for_update().select_related("house", "user"), pk=pk)
        if booking.user_id == request.user.pk:
            return Response({"detail": "You cannot review your own booking request."}, status=403)
        if booking.status != "pending":
            return Response({"detail": "Only pending booking requests can be reviewed."}, status=409)
        if decision == "confirmed" and not booking.house.is_free(booking.check_in, booking.check_out):
            return Response({"detail": "These dates have since been reserved. The request remains pending."}, status=409)
        booking.status = decision
        booking.save(update_fields=["status"])
        mark_manager_request_read(request.user, booking)
        create_decision_notification(booking)
    send_booking_email(booking, "decision")
    return Response(BookingSerializer(booking).data)


@api_view(["POST"])
@permission_classes([IsManager])
def manager_booking_approve(request, pk):
    return decide_booking(request, pk, "confirmed")


@api_view(["POST"])
@permission_classes([IsManager])
def manager_booking_reject(request, pk):
    return decide_booking(request, pk, "rejected")


@api_view(["POST"])
@permission_classes([IsManager])
def manager_booking_clarify(request, pk):
    serializer = BookingClarificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update().select_related("house", "user"), pk=pk)
        if booking.user_id == request.user.pk:
            return Response({"detail": "You cannot review your own booking request."}, status=403)
        if booking.status != "pending":
            return Response({"detail": "Only pending booking requests can be clarified."}, status=409)
        if BookingNotification.objects.filter(
            user=booking.user, booking=booking, kind="booking_clarification"
        ).exists():
            return Response({"detail": "A clarification has already been requested for this booking."}, status=409)
        create_clarification_notification(booking, serializer.validated_data["message"])
        mark_manager_request_read(request.user, booking)
    return Response({"detail": "Clarification request sent.", "booking_id": booking.pk})


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
    booking_totals = {row["user_id"]: row["total"] for row in Booking.objects.filter(
        user_id__in=user_ids).values("user_id").annotate(total=Count("id"))}
    results = [{"id": user.id, "username": user.username, "email": user.email,
                "date_joined": user.date_joined, "is_active": user.is_active,
                "bookings_count": booking_totals.get(user.pk, 0)} for user in page]
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
    return Response({"id": user.id, "username": user.username, "email": user.email,
                     "date_joined": user.date_joined, "is_active": user.is_active,
                     "bookings": list(bookings.values("id", "house__name", "check_in", "check_out", "total_price", "status"))})


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_invitation(invitation, token):
    base = getattr(settings, "URBAN_NEST_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    link = f"{base}/manager/invitations/accept/{token}"
    delivered = send_mail("Urban Nest manager invitation", f"Accept your manager invitation: {link}\nThis invitation expires in 7 days.", settings.DEFAULT_FROM_EMAIL, [invitation.email], fail_silently=False)
    if delivered != 1:
        raise RuntimeError("Email backend did not confirm delivery.")


@api_view(["GET", "POST"])
@permission_classes([IsMainManager])
def manager_invitations(request):
    if request.method == "POST":
        mail_backend = settings.EMAIL_BACKEND
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
