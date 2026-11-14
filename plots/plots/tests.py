from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Booking, House, MpesaPayment

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
