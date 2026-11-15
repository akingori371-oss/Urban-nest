import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import BookingNotification

logger = logging.getLogger(__name__)


def manager_users():
    User = get_user_model()
    return User.objects.filter(is_superuser=True) | User.objects.filter(manager_profile__isnull=False)


def create_submission_notifications(booking):
    BookingNotification.objects.get_or_create(
        user=booking.user, booking=booking, kind="booking_received",
        defaults={
            "title": "Booking request received",
            "message": "Your booking request is awaiting manager approval.",
        },
    )
    for user in manager_users().distinct():
        BookingNotification.objects.get_or_create(
            user=user, booking=booking, kind="manager_booking_request",
            defaults={
                "title": "New booking request",
                "message": f"{booking.user.username} requested {booking.house.name}.",
            },
        )


def create_decision_notification(booking):
    decision = "approved" if booking.status == "confirmed" else "rejected"
    title = "Booking confirmed" if booking.status == "confirmed" else "Booking request update"
    message = (f"Your request for {booking.house.name} was {decision}. "
               f"Dates: {booking.check_in} to {booking.check_out}.")
    return BookingNotification.objects.get_or_create(
        user=booking.user, booking=booking, kind="booking_decision",
        defaults={"title": title, "message": message},
    )[0]


def send_booking_email(booking, event):
    if not booking.user.email:
        return False
    if event == "received":
        subject = "Urban Nest - Booking Request Received"
        body = (
            f"Hello {booking.user.get_full_name() or booking.user.username},\n\n"
            f"Apartment: {booking.house.name}\n"
            f"Check-in: {booking.check_in}\nCheck-out: {booking.check_out}\n"
            f"Nights: {booking.nights}\n"
            f"Estimated booking cost: KSh {booking.total_price}\n\n"
            "Your request is awaiting manager approval. You will receive a notification when the manager reviews it."
        )
    elif booking.status == "confirmed":
        subject = "Urban Nest - Booking Confirmed"
        body = (
            f"Hello {booking.user.get_full_name() or booking.user.username},\n\n"
            f"Your reservation at {booking.house.name} was approved.\n"
            f"Dates: {booking.check_in} to {booking.check_out}\n"
            f"Estimated booking cost: KSh {booking.total_price}."
        )
    else:
        subject = "Urban Nest - Booking Request Update"
        body = (
            f"Hello {booking.user.get_full_name() or booking.user.username},\n\n"
            f"Your request for {booking.house.name} ({booking.check_in} to {booking.check_out}) was not approved."
        )
    try:
        return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.user.email], fail_silently=False) == 1
    except Exception as exc:
        logger.warning("Booking email delivery failed (%s).", type(exc).__name__)
        return False


def mark_manager_request_read(user, booking):
    notification = BookingNotification.objects.filter(
        user=user, booking=booking, kind="manager_booking_request", read_at__isnull=True,
    ).first()
    if notification:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
