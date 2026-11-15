
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.signals import user_logged_in
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

from ..models import House, Booking, Announcement, BookingNotification
from ..booking_notifications import create_submission_notifications, manager_users, send_booking_email

from .serializers import (
    RegisterSerializer, HouseSerializer,
    BookingSerializer, HouseDetailSerializer
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
        qs = Booking.objects.filter(user=request.user).select_related("house").order_by("-created_at")
        return Response(BookingSerializer(qs, many=True).data)

    serializer = BookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if not manager_users().exists():
        return err("Booking requests are unavailable until a manager account is configured.", 503)
    values = serializer.validated_data
    with transaction.atomic():
        house = House.objects.select_for_update().get(pk=values["house"].pk)
        if not house.is_active:
            return err("This apartment is no longer available for booking.", 409)
        if not house.is_free(values["check_in"], values["check_out"]):
            return err("That apartment is already booked for those dates.")
        total = (values["check_out"] - values["check_in"]).days * house.price_per_night
        booking = serializer.save(user=request.user, house=house, total_price=total, status="pending")
        create_submission_notifications(booking)
    send_booking_email(booking, "received")
    return Response(BookingSerializer(booking).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    return Response(BookingSerializer(own_booking(request, pk)).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def booking_cancel(request, pk):
    with transaction.atomic():
        booking = get_object_or_404(Booking.objects.select_for_update(), pk=pk, user=request.user)
        if booking.status not in {"pending", "confirmed"}:
            return err("Only pending or confirmed bookings can be cancelled.", 409)
        booking.status = "cancelled"
        booking.save(update_fields=["status"])
    return Response(BookingSerializer(booking).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    customer_notifications = BookingNotification.objects.filter(
        user=request.user, kind__in=["booking_received", "booking_decision"])
    notifications = customer_notifications.select_related("booking", "booking__house")[:100]
    return Response({
        "unread_count": customer_notifications.filter(read_at__isnull=True).count(),
        "results": [{"id": n.pk, "booking_id": n.booking_id, "kind": n.kind, "title": n.title,
                     "message": n.message, "created_at": n.created_at, "read": n.read_at is not None}
                    for n in notifications],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read(request, pk):
    notification = get_object_or_404(BookingNotification.objects.filter(user=request.user), pk=pk)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return Response({"id": notification.pk, "read": True})


# ---------- Dashboard ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    announcements = [{"title": a.title, "message": a.message, "created_at": a.created_at}
                     for a in Announcement.objects.filter(is_published=True)
                     .filter(Q(recipients__isnull=True) | Q(recipients=request.user)).distinct()[:5]]
    return Response({"announcements": announcements,
                     "notifications_unread": BookingNotification.objects.filter(
                         user=request.user, kind__in=["booking_received", "booking_decision"],
                         read_at__isnull=True).count()})


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
