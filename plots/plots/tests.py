from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlparse
import re
import hashlib
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import (Announcement, Booking, House, ManagerInvitation,
                     ManagerProfile, MpesaPayment, PaymentPeriod)

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UrbanNestAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="guest", email="guest@example.test", password="StrongPass123!")
        self.other = User.objects.create_user(username="other", email="other@example.test", password="StrongPass123!")
        self.house = House.objects.create(name="Nest", location="Nairobi", bedrooms=1, price_per_night="1000.00")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.start = timezone.localdate() + timedelta(days=10)

    def booking(self, start=None, end=None):
        start = start or self.start
        end = end or start + timedelta(days=2)
        return self.client.post("/api/bookings/", {"house": self.house.pk, "check_in": str(start), "check_out": str(end)}, format="json")

    def test_overlap_and_back_to_back(self):
        self.assertEqual(self.booking().status_code, 201)
        self.assertEqual(self.booking(self.start + timedelta(days=1), self.start + timedelta(days=3)).status_code, 400)
        self.assertEqual(self.booking(self.start + timedelta(days=2), self.start + timedelta(days=4)).status_code, 201)

    def test_rejects_past_and_invalid_dates(self):
        past = timezone.localdate() - timedelta(days=1)
        self.assertEqual(self.booking(past, past + timedelta(days=1)).status_code, 400)
        self.assertEqual(self.booking(self.start, self.start).status_code, 400)

    def test_long_periods_created_once(self):
        response = self.booking(self.start, self.start + timedelta(days=65))
        booking = Booking.objects.get(pk=response.data["id"])
        booking.create_periods()
        self.assertEqual(list(booking.periods.values_list("number", flat=True)), [1, 2, 3])

    def test_booking_ownership(self):
        pk = self.booking().data["id"]
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(f"/api/bookings/{pk}/cancel/").status_code, 404)

    @patch("plots.api.api_views.initiate_stk_push")
    def test_pending_payment_reused(self, initiate):
        pk = self.booking().data["id"]
        initiate.return_value = {"ResponseCode": "0", "CheckoutRequestID": "checkout-1"}
        url = f"/api/pay/booking/{pk}/"
        first = self.client.post(url, {"phone": "0712345678"}, format="json")
        second = self.client.post(url, {"phone": "0712345678"}, format="json")
        self.assertEqual(first.data["id"], second.data["id"])
        initiate.assert_called_once()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_callback_receipt_and_ownership(self, initiate):
        pk = self.booking().data["id"]
        initiate.return_value = {"ResponseCode": "0", "CheckoutRequestID": "checkout-2"}
        started = self.client.post(f"/api/pay/booking/{pk}/", {"phone": "0712345678"}, format="json")
        payment = MpesaPayment.objects.get(pk=started.data["id"])
        callback = {"Body": {"stkCallback": {"CheckoutRequestID": "checkout-2", "ResultCode": 0, "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": int(payment.amount)}, {"Name": "PhoneNumber", "Value": 254712345678}, {"Name": "MpesaReceiptNumber", "Value": "QAB123XYZ"}]}}}}
        self.client.post("/api/mpesa/callback/", callback, format="json")
        self.client.post("/api/mpesa/callback/", callback, format="json")
        result = self.client.get(f"/api/payments/{payment.pk}/")
        self.assertEqual(result.data["status"], "success")
        self.assertEqual(result.data["receipt"], "QAB123XYZ")
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/payments/{payment.pk}/").status_code, 404)

    def test_house_listing_is_paginated_and_details_are_dynamic(self):
        for index in range(24):
            House.objects.create(name=f"Flat {index:02d}", location="Nairobi",
                                 bedrooms=2, price_per_night="1500.00")
        first = self.client.get("/api/houses/?page=1")
        second = self.client.get("/api/houses/?page=2")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["count"], 25)
        self.assertEqual(len(first.data["results"]), 20)
        self.assertIsNotNone(first.data["next"])
        self.assertIsNone(first.data["previous"])
        self.assertEqual(len(second.data["results"]), 5)
        self.assertIsNotNone(second.data["previous"])
        single = self.client.get("/api/houses/?search=Nest")
        self.assertEqual(single.data["count"], 1)
        detail = self.client.get(f"/api/houses/{self.house.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["name"], "Nest")
        self.assertIn("availability", detail.data)
        self.assertEqual(self.client.get("/api/houses/999999/").status_code, 404)

    def test_house_listing_rejects_invalid_page_and_requires_authentication(self):
        self.assertEqual(self.client.get("/api/houses/?page=abc").status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/houses/").status_code, 401)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}})
class ManagerAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.tenant = User.objects.create_user(username="tenant", email="tenant@example.test", password="StrongPass123!")
        self.other = User.objects.create_user(username="other", email="other@example.test", password="StrongPass123!")
        self.main = User.objects.create_user(username="main", email="akingori371@gmail.com", password="StrongPass123!")
        self.manager = User.objects.create_user(username="manager", email="manager@example.test", password="StrongPass123!")
        self.main_profile = ManagerProfile.objects.create(user=self.main, is_main=True)
        self.manager_profile = ManagerProfile.objects.create(user=self.manager)
        self.house = House.objects.create(name="Managed Nest", location="Nairobi", bedrooms=2, price_per_night="1200.00")
        self.client = APIClient()

    def auth(self, user):
        self.client.force_authenticate(user)

    def test_tenant_cannot_access_manager_endpoints(self):
        self.auth(self.tenant)
        self.assertEqual(self.client.get("/api/manager/dashboard/").status_code, 403)
        self.assertEqual(self.client.get("/api/manager/apartments/").status_code, 403)

    def test_invited_manager_has_operations_but_not_main_controls(self):
        self.auth(self.manager)
        self.assertEqual(self.client.get("/api/manager/dashboard/").status_code, 200)
        self.assertEqual(self.client.get("/api/manager/invitations/").status_code, 403)
        self.assertEqual(self.client.post("/api/manager/invitations/", {"email": "new@example.test"}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/manager/managers/").status_code, 403)

    def test_main_manager_can_invite_and_cancel_and_acceptance_is_single_use(self):
        self.auth(self.main)
        cancelled = self.client.post("/api/manager/invitations/", {"email": "cancelme@example.test"}, format="json")
        self.assertEqual(cancelled.status_code, 201)
        cancel_record = ManagerInvitation.objects.get(pk=cancelled.data["id"])
        self.assertEqual(self.client.delete(f"/api/manager/invitations/{cancel_record.pk}/").status_code, 204)
        cancel_record.refresh_from_db()
        self.assertEqual(cancel_record.status, "cancelled")
        response = self.client.post("/api/manager/invitations/", {"email": "newmanager@example.test"}, format="json")
        self.assertEqual(response.status_code, 201)
        invitation = ManagerInvitation.objects.get(pk=response.data["id"])
        self.assertEqual(len(mail.outbox), 2)
        token = re.search(r"/manager/invitations/accept/([^\s]+)", mail.outbox[1].body).group(1)
        self.assertEqual(invitation.token_hash, hashlib.sha256(token.encode()).hexdigest())
        invitee = get_user_model().objects.create_user(username="invitee", email="newmanager@example.test", password="StrongPass123!")
        self.auth(invitee)
        accepted = self.client.post(f"/api/manager/invitations/accept/{token}/", {}, format="json")
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(ManagerProfile.objects.filter(user=invitee, is_main=False).exists())
        self.assertEqual(self.client.post(f"/api/manager/invitations/accept/{token}/", {}, format="json").status_code, 404)
        self.auth(self.main)
        self.assertEqual(self.client.delete(f"/api/manager/managers/{ManagerProfile.objects.get(user=invitee).pk}/").status_code, 204)
        self.assertFalse(ManagerProfile.objects.filter(user=invitee).exists())

    def test_invitation_email_mismatch_expiry_and_reuse_are_rejected(self):
        token = "secret-token"
        invitation = ManagerInvitation.objects.create(email=self.manager.email, token_hash=hashlib.sha256(token.encode()).hexdigest(), invited_by=self.main, expires_at=timezone.now() + timedelta(days=1))
        self.auth(self.other)
        self.assertEqual(self.client.post(f"/api/manager/invitations/accept/{token}/", {}, format="json").status_code, 403)
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=["expires_at"])
        self.auth(self.manager)
        self.assertEqual(self.client.post(f"/api/manager/invitations/accept/{token}/", {}, format="json").status_code, 410)

    def test_public_registration_cannot_assign_manager_role(self):
        response = self.client.post("/api/auth/register/", {"username": "new", "email": "new@example.test", "password": "StrongPass123!", "is_manager": True, "is_superuser": True}, format="json")
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username="new")
        self.assertFalse(user.is_superuser)
        self.assertFalse(ManagerProfile.objects.filter(user=user).exists())

    def test_manager_can_create_edit_and_safely_deactivate_apartment(self):
        self.auth(self.manager)
        invalid = self.client.post("/api/manager/apartments/", {"name": "Bad Flat", "location": "Nairobi", "bedrooms": 0, "price_per_night": "950"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        created = self.client.post("/api/manager/apartments/", {"name": "New Flat", "location": "Nairobi", "bedrooms": 2, "price_per_night": "950"}, format="json")
        self.assertEqual(created.status_code, 201)
        pk = created.data["id"]
        self.assertEqual(self.client.patch(f"/api/manager/apartments/{pk}/", {"price_per_night": "1050"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/manager/apartments/{pk}/").status_code, 200)
        self.assertFalse(House.objects.get(pk=pk).is_active)
        bad_photo = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        self.assertEqual(self.client.post(f"/api/manager/apartments/{self.house.pk}/photos/", {"image": bad_photo}, format="multipart").status_code, 400)
        self.auth(self.tenant)
        self.assertEqual(self.client.post("/api/manager/apartments/", {}, format="json").status_code, 403)

    def test_manager_sees_all_bookings_and_tenant_sees_only_own(self):
        a = Booking.objects.create(user=self.tenant, house=self.house, check_in=timezone.localdate() + timedelta(days=3), check_out=timezone.localdate() + timedelta(days=5), total_price="2400")
        b = Booking.objects.create(user=self.other, house=House.objects.create(name="Other", location="Nairobi", price_per_night="500"), check_in=timezone.localdate() + timedelta(days=3), check_out=timezone.localdate() + timedelta(days=5), total_price="1000")
        self.auth(self.manager)
        results = self.client.get("/api/manager/bookings/").data["results"]
        self.assertEqual({row["id"] for row in results}, {a.id, b.id})
        self.auth(self.tenant)
        self.assertEqual(len(self.client.get("/api/bookings/").data), 1)

    def test_manager_cannot_mark_booking_paid_and_cannot_make_confirmed_overlap(self):
        existing = Booking.objects.create(user=self.tenant, house=self.house, check_in=timezone.localdate() + timedelta(days=4), check_out=timezone.localdate() + timedelta(days=7), total_price="3600")
        self.auth(self.manager)
        # Manager actions only allow confirmed -> cancelled; arbitrary status/paid fields are rejected.
        self.assertEqual(self.client.post(f"/api/manager/bookings/{existing.pk}/", {"status": "paid"}, format="json").status_code, 400)
        self.assertFalse(Booking.objects.get(pk=existing.pk).paid)
        self.auth(self.other)
        overlap = self.client.post("/api/bookings/", {"house": self.house.pk, "check_in": str(existing.check_in + timedelta(days=1)), "check_out": str(existing.check_out + timedelta(days=1))}, format="json")
        self.assertEqual(overlap.status_code, 400)

    def test_manager_payment_visibility_and_tenant_ownership(self):
        booking = Booking.objects.create(user=self.tenant, house=self.house, check_in=timezone.localdate() + timedelta(days=3), check_out=timezone.localdate() + timedelta(days=5), total_price="2400")
        payment = MpesaPayment.objects.create(booking=booking, phone="254712345678", amount="2400", status="pending")
        self.auth(self.manager)
        self.assertEqual(self.client.get("/api/manager/payments/").data["results"][0]["id"], payment.id)
        self.auth(self.other)
        self.assertEqual(self.client.get(f"/api/payments/{payment.pk}/").status_code, 404)
        self.auth(self.manager)
        self.assertEqual(self.client.patch(f"/api/manager/payments/{payment.pk}/", {"status": "success"}, format="json").status_code, 404)

    def test_announcements_targeting_and_dashboard_counts_database_records(self):
        Announcement.objects.create(title="Everyone", message="Hello", is_published=True)
        targeted = Announcement.objects.create(title="Only tenant", message="Hi", is_published=True)
        targeted.recipients.add(self.tenant)
        Announcement.objects.create(title="Draft", message="Not published", is_published=False)
        today = timezone.localdate()
        Booking.objects.create(user=self.tenant, house=self.house, check_in=today, check_out=today + timedelta(days=2), total_price="2400")
        self.auth(self.tenant)
        titles = {a["title"] for a in self.client.get("/api/dashboard/").data["announcements"]}
        self.assertEqual(titles, {"Everyone", "Only tenant"})
        self.auth(self.manager)
        dashboard = self.client.get("/api/manager/dashboard/").data
        self.assertEqual(dashboard["apartments_total"], 1)
        self.assertEqual(dashboard["apartments_available"], 0)
        self.assertEqual(dashboard["apartments_occupied"], 1)
        self.assertEqual(dashboard["tenants_total"], 2)
        self.assertEqual(dashboard["bookings_total"], 1)
        self.assertEqual(dashboard["outstanding_balance"], "2400")
        tenants = self.client.get("/api/manager/tenants/").data["results"]
        tenant_row = next(row for row in tenants if row["id"] == self.tenant.pk)
        self.assertEqual(tenant_row["outstanding_balance"], "2400")

    def test_manager_can_publish_announcement_to_selected_tenant(self):
        self.auth(self.manager)
        created = self.client.post("/api/manager/announcements/", {
            "title": "Water outage", "message": "Tomorrow morning", "is_published": False,
            "recipient_ids": [self.tenant.pk],
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.data["is_published"])
        published = self.client.patch(f"/api/manager/announcements/{created.data['id']}/", {"is_published": True}, format="json")
        self.assertTrue(published.data["is_published"])
        self.auth(self.tenant)
        self.assertIn("Water outage", {a["title"] for a in self.client.get("/api/dashboard/").data["announcements"]})
        self.auth(self.other)
        self.assertNotIn("Water outage", {a["title"] for a in self.client.get("/api/dashboard/").data["announcements"]})
