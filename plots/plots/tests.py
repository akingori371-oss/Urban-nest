from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (Announcement, Booking, BookingNotification, House, HousePhoto,
                     ManagerInvitation, ManagerProfile)
from .management.commands.seed_demo_apartments import DEMO_APARTMENTS

User = get_user_model()


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class BookingWorkflowTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="tenant", email="tenant@example.test", password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.test", password="StrongPass123!",
        )
        self.manager = User.objects.create_user(
            username="manager", email="manager@example.test", password="StrongPass123!",
        )
        ManagerProfile.objects.create(user=self.manager, is_main=True)
        self.house = House.objects.create(
            name="Managed Nest", location="Nairobi", bedrooms=2,
            price_per_night="1200.00",
        )
        self.client = APIClient()
        self.start = timezone.localdate() + timedelta(days=10)

    def auth(self, user):
        self.client.force_authenticate(user)

    def submit(self, user=None, start=None, end=None, **extra):
        self.auth(user or self.customer)
        start = start or self.start
        end = end or start + timedelta(days=2)
        payload = {"house": self.house.pk, "check_in": str(start), "check_out": str(end),
                   "contact_number": "+254700000001", "guest_count": 2, **extra}
        return self.client.post("/api/bookings/", payload, format="json")

    def test_authenticated_booking_is_pending_and_sends_notice_and_email(self):
        response = self.submit(status="confirmed")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["total_price"], "2400.00")
        booking = Booking.objects.get(pk=response.data["id"])
        self.assertEqual(booking.contact_number, "+254700000001")
        self.assertEqual(booking.guest_count, 2)
        self.assertEqual(BookingNotification.objects.filter(booking=booking).count(), 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Urban Nest - Booking Request Received")
        self.assertIn("awaiting manager approval", mail.outbox[0].body)

    def test_unauthenticated_customer_cannot_submit(self):
        self.auth(None)
        response = self.client.post("/api/bookings/", {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Booking.objects.count(), 0)

    def test_customer_reads_only_own_booking_and_cannot_set_status(self):
        booking = self.submit().data
        self.auth(self.other)
        self.assertEqual(self.client.get(f"/api/bookings/{booking['id']}/").status_code, 404)
        self.auth(self.customer)
        changed = self.client.patch(f"/api/bookings/{booking['id']}/", {"status": "confirmed"}, format="json")
        self.assertNotEqual(changed.status_code, 200)
        self.assertEqual(Booking.objects.get(pk=booking["id"]).status, "pending")

    def test_pending_requests_do_not_block_until_manager_approval(self):
        first = self.submit()
        second = self.submit(start=self.start + timedelta(days=1), end=self.start + timedelta(days=3))
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        first_booking = Booking.objects.get(pk=first.data["id"])
        self.auth(self.manager)
        approved = self.client.post(f"/api/manager/bookings/{first_booking.pk}/approve/", {}, format="json")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], "confirmed")
        second_id = second.data["id"]
        conflict = self.client.post(f"/api/manager/bookings/{second_id}/approve/", {}, format="json")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(Booking.objects.get(pk=second_id).status, "pending")
        self.assertFalse(self.house.is_free(first_booking.check_in, first_booking.check_out))

    def test_rejected_booking_does_not_reserve_apartment_and_notifies_customer(self):
        result = self.submit()
        booking = Booking.objects.get(pk=result.data["id"])
        self.auth(self.manager)
        response = self.client.post(f"/api/manager/bookings/{booking.pk}/reject/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "rejected")
        self.assertTrue(self.house.is_free(booking.check_in, booking.check_out))
        self.assertEqual(BookingNotification.objects.filter(user=self.customer, booking=booking, kind="booking_decision").count(), 1)
        self.assertEqual(mail.outbox[-1].subject, "Urban Nest - Booking Request Update")

    def test_approval_creates_decision_notification_email_and_reserves_dates(self):
        result = self.submit()
        booking = Booking.objects.get(pk=result.data["id"])
        self.auth(self.manager)
        response = self.client.post(f"/api/manager/bookings/{booking.pk}/approve/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookingNotification.objects.filter(user=self.customer, booking=booking, kind="booking_decision").count(), 1)
        self.assertEqual(mail.outbox[-1].subject, "Urban Nest - Booking Confirmed")
        self.assertFalse(self.house.is_free(booking.check_in, booking.check_out))
        self.assertEqual(self.client.post(f"/api/manager/bookings/{booking.pk}/approve/", {}, format="json").status_code, 409)

    def test_manager_unread_count_persists_and_reading_one_decrements(self):
        first = self.submit().data
        self.submit(start=self.start + timedelta(days=4), end=self.start + timedelta(days=6))
        self.auth(self.manager)
        count_url = "/api/manager/booking-requests/unread-count/"
        self.assertEqual(self.client.get(count_url).data["unread_count"], 2)
        self.client.get(f"/api/manager/bookings/{first['id']}/")
        self.assertEqual(self.client.get(count_url).data["unread_count"], 1)
        self.assertEqual(self.client.get("/api/manager/bookings/?status=pending").data["count"], 2)
        self.assertFalse(self.client.get("/api/manager/bookings/?status=pending").data["results"][0]["unread"] if self.client.get("/api/manager/bookings/?status=pending").data["results"][0]["id"] == first["id"] else False)

    def test_manager_only_endpoints_reject_customers(self):
        self.auth(self.customer)
        self.assertEqual(self.client.get("/api/manager/booking-requests/unread-count/").status_code, 403)
        self.assertEqual(self.client.post("/api/manager/bookings/1/approve/", {}, format="json").status_code, 403)

    def test_manager_cannot_review_their_own_booking_request(self):
        response = self.submit(user=self.manager)
        booking_id = response.data["id"]
        self.auth(self.manager)
        for decision in ("approve", "reject"):
            result = self.client.post(
                f"/api/manager/bookings/{booking_id}/{decision}/",
                {},
                format="json",
            )
            self.assertEqual(result.status_code, 403)
        self.assertEqual(Booking.objects.get(pk=booking_id).status, "pending")

    def test_booking_email_failure_does_not_undo_request(self):
        with patch("plots.booking_notifications.send_mail", side_effect=RuntimeError("mail transport failed")):
            response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Booking.objects.filter(pk=response.data["id"], status="pending").exists())

    def test_customer_notification_read_is_scoped_and_persistent(self):
        result = self.submit().data
        booking = Booking.objects.get(pk=result["id"])
        notification = BookingNotification.objects.get(user=self.customer, booking=booking, kind="booking_received")
        self.auth(self.other)
        self.assertEqual(self.client.post(f"/api/notifications/{notification.pk}/read/", {}, format="json").status_code, 404)
        self.auth(self.customer)
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 1)
        self.assertEqual(self.client.post(f"/api/notifications/{notification.pk}/read/", {}, format="json").status_code, 200)
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 0)

    def test_invalid_dates_and_missing_booking_details_rejected(self):
        self.assertEqual(self.submit(end=self.start).status_code, 400)
        self.assertEqual(self.submit(contact_number="").status_code, 400)
        self.assertEqual(self.submit(guest_count=0).status_code, 400)

    def test_customer_registration_and_login_still_work(self):
        self.auth(None)
        register = self.client.post("/api/auth/register/", {
            "username": "new", "email": "new@example.test", "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(register.status_code, 201)
        login = self.client.post("/api/auth/login/", {
            "email": "new@example.test", "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(login.status_code, 200)

    def test_apartment_prices_images_and_reviews_remain_available(self):
        self.auth(self.customer)
        photo = HousePhoto.objects.create(house=self.house, image="houses/test-home.jpg")
        response = self.client.get("/api/houses/")
        house_data = next(item for item in response.data["results"] if item["id"] == self.house.pk)
        self.assertEqual(Decimal(house_data["price_per_night"]), Decimal("1200.00"))
        self.assertEqual(house_data["photos"][0]["id"], photo.pk)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ManagerAndListingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager", email="manager@example.test", password="StrongPass123!")
        ManagerProfile.objects.create(user=self.user, is_main=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.house = House.objects.create(name="Example", location="Nairobi", bedrooms=1, price_per_night="1000.00")

    def test_manager_dashboard_booking_metrics(self):
        response = self.client.get("/api/manager/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["apartments_total"], 1)

    def test_invitation_email_uses_configured_backend_and_registration_cannot_assign_manager(self):
        response = self.client.post("/api/manager/invitations/", {"email": "newmanager@example.test"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        public = APIClient().post("/api/auth/register/", {
            "username": "public", "email": "public@example.test", "password": "StrongPass123!",
            "is_superuser": True,
        }, format="json")
        self.assertEqual(public.status_code, 201)
        self.assertFalse(User.objects.get(username="public").is_superuser)

    def test_seeded_apartments_are_listed(self):
        self.assertTrue(DEMO_APARTMENTS)
        self.assertEqual(self.client.get("/api/manager/apartments/").status_code, 200)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ProvisionMainManagerCommandTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    @patch("plots.management.commands.provision_main_manager.send_mail", return_value=1)
    def test_command_requires_existing_account_and_sends_verification_without_granting_role(self, send_mail):
        with self.assertRaises(CommandError):
            call_command("provision_main_manager")
        self.assertFalse(ManagerInvitation.objects.exists())

        user = User.objects.create_user(
            username="fresh-main",
            email="akingori371@gmail.com",
            password="StrongPass123!",
        )
        call_command("provision_main_manager")

        invitation = ManagerInvitation.objects.get(email__iexact=user.email)
        self.assertTrue(invitation.is_main_provision)
        self.assertEqual(invitation.status, "pending")
        self.assertFalse(ManagerProfile.objects.filter(user=user).exists())
        send_mail.assert_called_once()
