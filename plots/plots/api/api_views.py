
from datetime import timedelta
import hashlib
import hmac
import secrets

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import (
    House,
    Booking,
    Announcement,
    BookingNotification,
    PasswordResetOTP,
)
from ..booking_notifications import (
    create_submission_notifications,
    manager_users,
    send_booking_email,
)

from .serializers import (
    RegisterSerializer,
    HouseSerializer,
    BookingSerializer,
    HouseDetailSerializer,
    HouseSubmissionSerializer,
)


PASSWORD_RESET_COOKIE = "password_reset_authorization"
PASSWORD_RESET_COOKIE_PATH = "/api/auth/password-reset/"


def err(msg, code=400):
    return Response({"detail": msg}, status=code)


class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class IsManager(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return bool(
            user.is_superuser
            or getattr(user, "manager_profile", None)
        )


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

    found = get_user_model().objects.filter(
        email__iexact=email
    ).first()

    user = authenticate(
        username=found.username,
        password=password
    ) if found else None

    if user is None:
        return err("Invalid email or password.", 401)

    user_logged_in.send(
        sender=user.__class__,
        request=request,
        user=user
    )

    refresh = RefreshToken.for_user(user)
    profile = getattr(user, "manager_profile", None)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "username": user.username,
        "is_superuser": user.is_superuser,
        "is_manager": bool(user.is_superuser or profile),
        "is_main_manager": bool(
            user.is_superuser or (profile and profile.is_main)
        ),
    })


def _password_reset_otp_hash(user_id, otp):
    message = f"password-reset:{user_id}:{otp}".encode("utf-8")
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()


def _password_reset_authorization_hash(authorization):
    message = (
        f"password-reset-authorization:{authorization}".encode("utf-8")
    )

    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = (request.data.get("email") or "").strip()

    if not email:
        return err("Send an email address.")

    user = get_user_model().objects.filter(
        email__iexact=email
    ).first()

    if user:
        now = timezone.now()

        with transaction.atomic():
            reset, _ = PasswordResetOTP.objects.select_for_update().get_or_create(
                user=user,
                defaults={
                    "otp_hash": "",
                    "created_at": now,
                    "expires_at": now,
                    "last_sent_at": now - timedelta(seconds=60),
                },
            )

            if now < reset.last_sent_at + timedelta(seconds=60):
                return Response({
                    "detail": (
                        "If an account exists for that email, "
                        "a verification code will be sent."
                    )
                })

            otp = f"{secrets.randbelow(1_000_000):06d}"

            reset.otp_hash = _password_reset_otp_hash(user.pk, otp)
            reset.created_at = now
            reset.expires_at = now + timedelta(minutes=10)
            reset.last_sent_at = now
            reset.attempts = 0
            reset.consumed_at = None
            reset.reset_authorization_hash = None
            reset.reset_authorization_expires_at = None
            reset.save()

            sent = send_mail(
                "Urban Nest password reset code",
                f"Your password reset code is {otp}. It expires in 10 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            if not sent:
                raise RuntimeError(
                    "Password reset email was not accepted for delivery."
                )

    return Response({
        "detail": (
            "If an account exists for that email, "
            "a verification code will be sent."
        )
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_verify(request):
    email = (request.data.get("email") or "").strip()
    otp = request.data.get("otp")

    if not email or not isinstance(otp, str):
        return err("Send an email address and verification code.")

    user = get_user_model().objects.filter(
        email__iexact=email
    ).first()

    if not user:
        return err("The verification code is invalid or expired.")

    with transaction.atomic():
        reset = PasswordResetOTP.objects.select_for_update().filter(
            user=user
        ).first()

        now = timezone.now()

        if (
            reset is None
            or reset.consumed_at is not None
            or reset.expires_at <= now
            or reset.attempts >= 5
        ):
            return err("The verification code is invalid or expired.")

        expected_hash = _password_reset_otp_hash(user.pk, otp)

        if not hmac.compare_digest(reset.otp_hash, expected_hash):
            reset.attempts += 1

            if reset.attempts >= 5:
                reset.consumed_at = now
                reset.otp_hash = ""

            reset.save(
                update_fields=["attempts", "consumed_at", "otp_hash"]
            )

            return err("The verification code is invalid or expired.")

        authorization = secrets.token_urlsafe(32)

        reset.consumed_at = now
        reset.otp_hash = ""
        reset.reset_authorization_hash = (
            _password_reset_authorization_hash(authorization)
        )
        reset.reset_authorization_expires_at = now + timedelta(minutes=10)

        reset.save(update_fields=[
            "consumed_at",
            "otp_hash",
            "reset_authorization_hash",
            "reset_authorization_expires_at",
        ])

    response = Response({
        "detail": "Verification code accepted."
    })

    response.set_cookie(
    PASSWORD_RESET_COOKIE,
    authorization,
    max_age=600,
    httponly=True,
    secure=not settings.DEBUG,
    samesite="None" if not settings.DEBUG else "Lax",
    path=PASSWORD_RESET_COOKIE_PATH,
)

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_complete(request):
    authorization = request.COOKIES.get(PASSWORD_RESET_COOKIE)
    password = request.data.get("password")

    if not authorization or not isinstance(password, str) or not password:
        return err(
            "A valid reset authorization and new password are required."
        )

    authorization_hash = _password_reset_authorization_hash(authorization)

    with transaction.atomic():
        reset = PasswordResetOTP.objects.select_for_update().filter(
            reset_authorization_hash=authorization_hash,
        ).first()

        now = timezone.now()

        if (
            reset is None
            or reset.reset_authorization_expires_at is None
            or reset.reset_authorization_expires_at <= now
        ):
            response = err(
                "The reset authorization is invalid or expired."
            )
            response.delete_cookie(
                PASSWORD_RESET_COOKIE,
                path=PASSWORD_RESET_COOKIE_PATH
            )
            return response

        user = get_user_model().objects.select_for_update().get(
            pk=reset.user_id
        )

        try:
            validate_password(password, user)
        except ValidationError as exc:
            return err(" ".join(exc.messages))

        user.set_password(password)
        user.save(update_fields=["password"])

        reset.reset_authorization_hash = None
        reset.reset_authorization_expires_at = None

        reset.save(update_fields=[
            "reset_authorization_hash",
            "reset_authorization_expires_at"
        ])

    response = Response({
        "detail": "Password reset successfully."
    })

    response.delete_cookie(
        PASSWORD_RESET_COOKIE,
        path=PASSWORD_RESET_COOKIE_PATH
    )

    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    profile = getattr(u, "manager_profile", None)

    return Response({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "is_manager": bool(u.is_superuser or profile),
        "is_main_manager": bool(
            u.is_superuser or (profile and profile.is_main)
        )
    })


# ---------- Houses ----------

class HousePagination(PageNumberPagination):
    page_size = 20
    page_query_param = "page"


def validate_house_dates(request):
    raw_in = request.query_params.get("check_in")
    raw_out = request.query_params.get("check_out")

    if bool(raw_in) != bool(raw_out):
        return None, None, err(
            "Send both check_in and check_out as YYYY-MM-DD."
        )

    if not raw_in:
        return None, None, None

    cin = parse_date(raw_in)
    cout = parse_date(raw_out)

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

    qs = House.objects.filter(
        is_active=True,
        approval_status="approved"
    ).prefetch_related("photos").annotate(
        avg_rating=Avg("reviews__rating"),
        review_count=Count("reviews")
    )

    if cin and cout:
        busy = Booking.objects.filter(
            status="confirmed",
            check_in__lt=cout,
            check_out__gt=cin
        ).values_list("house_id", flat=True)

        qs = qs.exclude(id__in=busy)

    search = request.query_params.get("search", "").strip()

    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(location__icontains=search)
            | Q(county__icontains=search)
            | Q(property_type__icontains=search)
            | Q(description__icontains=search)
        )

    county = request.query_params.get("county", "").strip()
    property_type = request.query_params.get(
        "property_type", ""
    ).strip()

    if county:
        qs = qs.filter(county__iexact=county)

    if property_type:
        qs = qs.filter(property_type__iexact=property_type)

    ordering = request.query_params.get("ordering", "id")

    allowed_ordering = {
        "id",
        "name",
        "location",
        "county",
        "property_type",
        "bedrooms",
        "price_per_night",
    }

    if ordering.lstrip("-") not in allowed_ordering:
        return err("Unsupported ordering field.")

    qs = qs.order_by(ordering)

    paginator = HousePagination()
    page = paginator.paginate_queryset(qs, request)

    return paginator.get_paginated_response(
        HouseSerializer(
            page,
            many=True,
            context={"request": request}
        ).data
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def house_detail(request, pk):
    cin, cout, date_error = validate_house_dates(request)

    if date_error:
        return date_error

    house = get_object_or_404(
        House.objects.filter(
            is_active=True,
            approval_status="approved"
        ).prefetch_related(
            "photos"
        ).annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews")
        ).prefetch_related("reviews"),
        pk=pk
    )

    return Response(
        HouseDetailSerializer(
            house,
            context={"request": request}
        ).data
    )


# ---------- Property submissions ----------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def my_houses(request):
    if request.method == "GET":
        houses = House.objects.filter(
            owner=request.user
        ).order_by("-created_at")

        serializer = HouseSubmissionSerializer(
            houses,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    serializer = HouseSubmissionSerializer(
        data=request.data,
        context={"request": request}
    )

    serializer.is_valid(raise_exception=True)
    house = serializer.save()

    return Response(
        HouseSubmissionSerializer(
            house,
            context={"request": request}
        ).data,
        status=201
    )


@api_view(["GET", "PATCH", "PUT"])
@permission_classes([IsAuthenticated])
def manage_my_house(request, pk):
    house = get_object_or_404(
        House,
        pk=pk,
        owner=request.user
    )

    if request.method == "GET":
        return Response(
            HouseSubmissionSerializer(
                house,
                context={"request": request}
            ).data
        )

    serializer = HouseSubmissionSerializer(
        house,
        data=request.data,
        partial=request.method == "PATCH",
        context={"request": request}
    )

    serializer.is_valid(raise_exception=True)

    # Changes to a property require a fresh admin review.
    house = serializer.save(
        approval_status="pending",
        reviewed_by=None,
        reviewed_at=None
    )

    return Response(
        HouseSubmissionSerializer(
            house,
            context={"request": request}
        ).data
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_my_house(request, pk):
    house = get_object_or_404(
        House,
        pk=pk,
        owner=request.user
    )

    is_active = request.data.get("is_active")

    if not isinstance(is_active, bool):
        return err("Send is_active as true or false.")

    house.is_active = is_active
    house.save(update_fields=["is_active", "updated_at"])

    return Response({
        "id": house.pk,
        "is_active": house.is_active,
        "detail": (
            "Property activated successfully."
            if is_active
            else "Property deactivated successfully."
        )
    })


# ---------- Admin property approval ----------

@api_view(["GET"])
@permission_classes([IsManager])
def pending_houses(request):
    houses = House.objects.filter(
        approval_status="pending"
    ).select_related("owner").order_by("-created_at")

    serializer = HouseSubmissionSerializer(
        houses,
        many=True,
        context={"request": request}
    )

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsManager])
def review_house(request, pk):
    house = get_object_or_404(House, pk=pk)

    if house.approval_status != "pending":
        return err(
            "This property has already been reviewed.",
            409
        )

    decision = request.data.get("approval_status")

    if decision not in ["approved", "rejected"]:
        return err(
            "Choose either approved or rejected."
        )

    house.approval_status = decision
    house.reviewed_by = request.user
    house.reviewed_at = timezone.now()

    house.save(update_fields=[
        "approval_status",
        "reviewed_by",
        "reviewed_at"
    ])

    return Response({
        "id": house.pk,
        "approval_status": house.approval_status,
        "reviewed_at": house.reviewed_at,
        "detail": f"Property {decision} successfully."
    })


# ---------- Bookings ----------

def own_booking(request, pk):
    return get_object_or_404(
        Booking.objects.select_related("house"),
        pk=pk,
        user=request.user
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def booking_list(request):
    if request.method == "GET":
        qs = Booking.objects.filter(
            user=request.user
        ).select_related("house").order_by("-created_at")

        return Response(
            BookingSerializer(qs, many=True).data
        )

    serializer = BookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    if not manager_users().exists():
        return err(
            "Booking requests are unavailable until a manager account is configured.",
            503
        )

    values = serializer.validated_data

    with transaction.atomic():
        house = House.objects.select_for_update().get(
            pk=values["house"].pk
        )

        if not house.is_active or house.approval_status != "approved":
            return err(
                "This apartment is no longer available for booking.",
                409
            )

        if not house.is_free(
            values["check_in"],
            values["check_out"]
        ):
            return err(
                "That apartment is already booked for those dates."
            )

        total = (
            values["check_out"] - values["check_in"]
        ).days * house.price_per_night

        booking = serializer.save(
            user=request.user,
            house=house,
            total_price=total,
            status="pending"
        )

        create_submission_notifications(booking)

    send_booking_email(booking, "received")

    return Response(
        BookingSerializer(booking).data,
        status=201
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    return Response(
        BookingSerializer(
            own_booking(request, pk)
        ).data
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def booking_cancel(request, pk):
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=pk,
            user=request.user
        )

        if booking.status not in {"pending", "confirmed"}:
            return err(
                "Only pending or confirmed bookings can be cancelled.",
                409
            )

        booking.status = "cancelled"
        booking.save(update_fields=["status"])

    return Response(
        BookingSerializer(booking).data
    )


# ---------- Notifications ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    customer_notifications = BookingNotification.objects.filter(
        user=request.user,
        kind__in=[
            "booking_received",
            "booking_decision",
            "booking_clarification"
        ]
    )

    notifications = customer_notifications.select_related(
        "booking",
        "booking__house"
    )[:100]

    return Response({
        "unread_count": customer_notifications.filter(
            read_at__isnull=True
        ).count(),

        "results": [
            {
                "id": n.pk,
                "booking_id": n.booking_id,
                "kind": n.kind,
                "title": n.title,
                "message": n.message,
                "created_at": n.created_at,
                "read": n.read_at is not None
            }
            for n in notifications
        ]
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read(request, pk):
    notification = get_object_or_404(
        BookingNotification.objects.filter(user=request.user),
        pk=pk
    )

    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])

    return Response({
        "id": notification.pk,
        "read": True
    })


# ---------- Dashboard ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    announcements = [
        {
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at
        }
        for a in Announcement.objects.filter(
            is_published=True
        ).filter(
            Q(recipients__isnull=True)
            | Q(recipients=request.user)
        ).distinct()[:5]
    ]

    return Response({
        "announcements": announcements,
        "notifications_unread": BookingNotification.objects.filter(
            user=request.user,
            kind__in=[
                "booking_received",
                "booking_decision",
                "booking_clarification"
            ],
            read_at__isnull=True
        ).count()
    })


# ---------- Superuser only ----------

@api_view(["GET"])
@permission_classes([IsSuperuser])
def user_list(request):
    users = get_user_model().objects.all().order_by("id")

    return Response([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_superuser": u.is_superuser,
            "date_joined": u.date_joined,
            "bookings": Booking.objects.filter(user=u).count(),
        }
        for u in users
    ])


@api_view(["GET"])
@permission_classes([IsSuperuser])
def user_detail(request, pk):
    u = get_object_or_404(
        get_user_model(),
        pk=pk
    )

    bookings = Booking.objects.filter(
        user=u
    ).select_related("house").order_by("-check_in")

    return Response({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "bookings": BookingSerializer(
            bookings,
            many=True
        ).data,
    })
