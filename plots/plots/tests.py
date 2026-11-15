from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch
from urllib.parse import urlparse
import json
import re
import hashlib
import base64
import requests
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import (Announcement, Booking, House, ManagerInvitation,
                     ManagerProfile, MpesaPayment, PaymentPeriod, Review)
from .api_error_middleware import ApiErrorMiddleware
from .api.api_views import DarajaRequestError
from .management.commands.seed_demo_apartments import DEMO_APARTMENTS, marker_for


class ApiErrorMiddlewareTests(TestCase):
    def test_api_exception_returns_generic_json_and_logs_exception(self):
        request = RequestFactory().get("/api/houses/?page=1")
        error = RuntimeError("database password and SQL must not be returned")

        with self.assertLogs("django.request", level="ERROR") as captured:
            response = ApiErrorMiddleware(get_response=lambda _request: None).process_exception(request, error)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(json.loads(response.content), {"detail": "An unexpected server error occurred. Please try again later."})
        self.assertIn("RuntimeError: database password and SQL must not be returned", captured.output[0])
        self.assertNotIn("database password", response.content.decode())

    def test_non_api_exception_is_not_rewritten(self):
        request = RequestFactory().get("/houses/")
        self.assertIsNone(ApiErrorMiddleware(get_response=lambda _request: None).process_exception(request, RuntimeError("page error")))


class DemoApartmentSeedTests(TestCase):
    def setUp(self):
        self.existing = House.objects.create(
            name="Existing tenant home",
            location="Nairobi County - Kilimani",
            description="A user-created listing.",
            bedrooms=2,
            price_per_night="3000.00",
        )

    def test_seed_creates_exact_records_only_and_is_idempotent(self):
        preview = StringIO()
        call_command("seed_demo_apartments", dry_run=True, stdout=preview)
        self.assertIn("50 would be created; 0 already current; 0 would be price-updated", preview.getvalue())
        self.assertEqual(House.objects.count(), 1)

        call_command("seed_demo_apartments", stdout=StringIO())
        call_command("seed_demo_apartments", stdout=StringIO())

        demo_houses = House.objects.filter(description__contains="[[URBAN_NEST_DEMO|")
        self.assertEqual(len(DEMO_APARTMENTS), 50)
        self.assertEqual(demo_houses.count(), 50)
        self.assertEqual(House.objects.count(), 51)
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.description, "A user-created listing.")
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(Review.objects.count(), 0)
        self.assertEqual(get_user_model().objects.count(), 0)

        expected_counties = {
            "Nairobi County": 10,
            "Kiambu County": 10,
            "Mombasa County": 10,
            "Nakuru County": 10,
            "Machakos County": 10,
        }
        for county, expected in expected_counties.items():
            self.assertEqual(
                demo_houses.filter(location__startswith=f"{county} -").count(),
                expected,
            )

        for apartment in DEMO_APARTMENTS:
            self.assertTrue(demo_houses.filter(description__startswith=marker_for(apartment)).exists())

    def test_seed_stores_whole_nightly_prices_and_keeps_demo_labels(self):
        call_command("seed_demo_apartments", stdout=StringIO())
        bedsitter = House.objects.get(description__startswith="[[URBAN_NEST_DEMO|ID=NBI-04|")
        self.assertEqual(bedsitter.bedrooms, 0)
        self.assertEqual(bedsitter.price_per_night, Decimal("1200.00"))
        self.assertIn("NIGHTLY=1200|TYPE=Bedsitter|RATING=4.2", bedsitter.description)
        self.assertIn("Fictional demonstration listing.", bedsitter.description)
        prices = [apartment[6] for apartment in DEMO_APARTMENTS]
        self.assertTrue(all(isinstance(price, int) and 1 <= price < 5000 for price in prices))

    def test_seed_updates_only_existing_demo_price_and_marker(self):
        user = get_user_model().objects.create_user(username="price-check", password="not-used")
        house = House.objects.create(
            name="Existing demo home",
            location="Nairobi County - Kilimani",
            description="[[URBAN_NEST_DEMO|ID=NBI-01|MONTHLY=96000|TYPE=2-bedroom|RATING=4.8]] Keep this description.",
            bedrooms=2,
            price_per_night="1000.00",
        )
        booking = Booking.objects.create(
            user=user,
            house=house,
            check_in=timezone.localdate() + timedelta(days=3),
            check_out=timezone.localdate() + timedelta(days=5),
            total_price="6400.00",
        )
        payment = MpesaPayment.objects.create(
            booking=booking,
            phone="254700000000",
            amount="6400.00",
            status="pending",
        )

        preview = StringIO()
        call_command("seed_demo_apartments", dry_run=True, stdout=preview)
        self.assertIn("1 would be price-updated", preview.getvalue())
        house.refresh_from_db()
        self.assertEqual(house.price_per_night, Decimal("1000.00"))
        self.assertIn("MONTHLY=96000", house.description)

        call_command("seed_demo_apartments", stdout=StringIO())

        house.refresh_from_db()
        booking.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(house.price_per_night, Decimal("3200.00"))
        self.assertTrue(house.description.startswith(
            "[[URBAN_NEST_DEMO|ID=NBI-01|NIGHTLY=3200|TYPE=2-bedroom|RATING=4.8]] Keep this description."
        ))
        self.assertEqual(house.name, "Existing demo home")
        self.assertEqual(house.location, "Nairobi County - Kilimani")
        self.assertEqual(booking.total_price, Decimal("6400.00"))
        self.assertEqual(payment.amount, Decimal("6400.00"))
        self.assertEqual(payment.status, "pending")

    def test_all_demo_listings_are_paginated_searchable_and_have_no_fake_reviews(self):
        call_command("seed_demo_apartments", stdout=StringIO())
        user = get_user_model().objects.create_user(username="demo-check", password="not-used")
        client = APIClient()
        client.force_authenticate(user)

        pages = [client.get(f"/api/houses/?page={page}") for page in (1, 2, 3)]
        self.assertTrue(all(response.status_code == 200 for response in pages))
        self.assertEqual([len(response.data["results"]) for response in pages], [20, 20, 11])
        self.assertEqual([response.data["count"] for response in pages], [51, 51, 51])

        kiambu = client.get("/api/houses/?search=Kiambu%20County")
        self.assertEqual(kiambu.data["count"], 10)
        demo_response = client.get("/api/houses/?search=Greenview%20Residences")
        listing = demo_response.data["results"][0]
        self.assertIsNone(listing["avg_rating"])
        self.assertEqual(listing["review_count"], 0)
        self.assertEqual(Review.objects.count(), 0)

    def test_demo_studio_and_bedsitter_remain_editable_with_zero_bedrooms(self):
        call_command("seed_demo_apartments", stdout=StringIO())
        manager = get_user_model().objects.create_user(username="demo-manager", password="not-used")
        ManagerProfile.objects.create(user=manager)
        compact = House.objects.get(description__startswith="[[URBAN_NEST_DEMO|ID=NBI-04|")
        client = APIClient()
        client.force_authenticate(manager)

        response = client.patch(
            f"/api/manager/apartments/{compact.pk}/",
            {"bedrooms": 0},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        compact.refresh_from_db()
        self.assertEqual(compact.bedrooms, 0)
        self.assertTrue(compact.description.startswith("[[URBAN_NEST_DEMO|ID=NBI-04|"))


@override_settings(
    MPESA_CONSUMER_KEY="test-consumer-key",
    MPESA_CONSUMER_SECRET="test-consumer-secret",
    MPESA_SHORTCODE="174379",
    MPESA_PASSKEY="test-passkey",
    MPESA_API_BASE_URL="https://sandbox.safaricom.co.ke",
    MPESA_TRANSACTION_TYPE="CustomerPayBillOnline",
)
class DarajaClientTests(TestCase):
    def setUp(self):
        from .api import api_views
        api_views._clear_mpesa_token_cache()

    def test_oauth_uses_basic_auth_and_caches_token_until_expiry(self):
        from .api.api_views import mpesa_access_token
        response = Mock()
        response.json.return_value = {"access_token": "mock-token", "expires_in": "3600"}

        with patch("plots.api.api_views.requests.get", return_value=response) as get:
            self.assertEqual(mpesa_access_token(), "mock-token")
            self.assertEqual(mpesa_access_token(), "mock-token")

        get.assert_called_once_with(
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            auth=("test-consumer-key", "test-consumer-secret"),
            timeout=(5, 15),
        )

    def test_oauth_rejects_missing_credentials_timeout_and_invalid_response(self):
        from .api.api_views import mpesa_access_token

        with override_settings(MPESA_CONSUMER_KEY=None), self.assertRaises(DarajaRequestError):
            mpesa_access_token()

        with patch("plots.api.api_views.requests.get", side_effect=requests.Timeout):
            with self.assertRaises(DarajaRequestError) as timeout:
                mpesa_access_token()
            self.assertEqual(timeout.exception.stage, "OAuth")

        unauthorized = Mock(status_code=401)
        unauthorized.raise_for_status.side_effect = requests.HTTPError(
            "sensitive vendor response", response=unauthorized
        )
        with patch("plots.api.api_views.requests.get", return_value=unauthorized):
            with self.assertRaises(DarajaRequestError) as invalid_credentials:
                mpesa_access_token()
            self.assertNotIn("sensitive vendor response", invalid_credentials.exception.detail)
            self.assertNotIn("test-consumer-secret", invalid_credentials.exception.detail)

        response = Mock()
        response.json.return_value = {"unexpected": True}
        with patch("plots.api.api_views.requests.get", return_value=response):
            with self.assertRaises(DarajaRequestError):
                mpesa_access_token()

    def test_stk_push_builds_daraja_payload_and_password(self):
        from .api.api_views import initiate_stk_push
        response = Mock()
        response.json.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-test",
            "MerchantRequestID": "merchant-test",
        }

        with patch("plots.api.api_views.mpesa_access_token", return_value="mock-token"), patch(
            "plots.api.api_views.requests.post", return_value=response
        ) as post:
            result = initiate_stk_push("254712345678", 2400, "BOOKING-1")

        self.assertEqual(result["CheckoutRequestID"], "checkout-test")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer mock-token")
        payload = kwargs["json"]
        self.assertEqual(
            set(payload),
            {"BusinessShortCode", "Password", "Timestamp", "TransactionType", "Amount",
             "PartyA", "PartyB", "PhoneNumber", "CallBackURL", "AccountReference", "TransactionDesc"},
        )
        self.assertEqual(payload["PartyA"], "254712345678")
        self.assertEqual(payload["PhoneNumber"], "254712345678")
        self.assertEqual(payload["Amount"], 2400)
        password = f"174379test-passkey{payload['Timestamp']}".encode()
        self.assertEqual(payload["Password"], base64.b64encode(password).decode())

    def test_stk_rejection_timeout_and_missing_ids_are_distinguished(self):
        from .api.api_views import initiate_stk_push

        rejected = Mock()
        rejected.json.return_value = {"ResponseCode": "1"}
        with patch("plots.api.api_views.mpesa_access_token", return_value="token"), patch(
            "plots.api.api_views.requests.post", return_value=rejected
        ):
            with self.assertRaises(DarajaRequestError) as error:
                initiate_stk_push("254712345678", 2400, "BOOKING-1")
            self.assertFalse(error.exception.outcome_uncertain)

        with patch("plots.api.api_views.mpesa_access_token", return_value="token"), patch(
            "plots.api.api_views.requests.post", side_effect=requests.Timeout
        ):
            with self.assertRaises(DarajaRequestError) as error:
                initiate_stk_push("254712345678", 2400, "BOOKING-1")
            self.assertTrue(error.exception.outcome_uncertain)

        missing_ids = Mock()
        missing_ids.json.return_value = {"ResponseCode": "0", "CheckoutRequestID": "checkout-only"}
        with patch("plots.api.api_views.mpesa_access_token", return_value="token"), patch(
            "plots.api.api_views.requests.post", return_value=missing_ids
        ):
            with self.assertRaises(DarajaRequestError) as error:
                initiate_stk_push("254712345678", 2400, "BOOKING-1")
            self.assertTrue(error.exception.outcome_uncertain)
            self.assertEqual(error.exception.response["CheckoutRequestID"], "checkout-only")

    def test_stk_query_uses_the_checkout_id_and_required_password(self):
        from .api.api_views import query_stk_push
        response = Mock()
        response.json.return_value = {"ResponseCode": "0", "ResultCode": "0"}

        with patch("plots.api.api_views.mpesa_access_token", return_value="mock-token"), patch(
            "plots.api.api_views.requests.post", return_value=response
        ) as post:
            query_stk_push("checkout-query")

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query")
        payload = kwargs["json"]
        self.assertEqual(payload["CheckoutRequestID"], "checkout-query")
        self.assertEqual(
            payload["Password"],
            base64.b64encode(
                f"174379test-passkey{payload['Timestamp']}".encode()
            ).decode(),
        )


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    MPESA_CALLBACK_URL_VALID=True,
    MPESA_CONSUMER_KEY="test-consumer-key",
    MPESA_CONSUMER_SECRET="test-consumer-secret",
    MPESA_SHORTCODE="174379",
    MPESA_PASSKEY="test-passkey",
)
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
    def test_user_cannot_initiate_payment_for_another_users_booking_or_period(self, initiate):
        short_booking = self.booking()
        long_booking = self.booking(self.start + timedelta(days=2), self.start + timedelta(days=67))
        period = PaymentPeriod.objects.get(booking_id=long_booking.data["id"], number=1)
        self.client.force_authenticate(self.other)

        booking_response = self.client.post(
            f"/api/pay/booking/{short_booking.data['id']}/",
            {"phone": "0712345678"},
            format="json",
        )
        period_response = self.client.post(
            f"/api/pay/period/{period.pk}/",
            {"phone": "0712345678"},
            format="json",
        )

        self.assertEqual(booking_response.status_code, 404)
        self.assertEqual(period_response.status_code, 404)
        self.assertEqual(MpesaPayment.objects.count(), 0)
        initiate.assert_not_called()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_pending_payment_reused(self, initiate):
        pk = self.booking().data["id"]
        initiate.return_value = {"ResponseCode": "0", "CheckoutRequestID": "checkout-1", "MerchantRequestID": "merchant-1"}
        url = f"/api/pay/booking/{pk}/"
        first = self.client.post(url, {"phone": "0712345678", "amount": 1}, format="json")
        second = self.client.post(url, {"phone": "0712345678"}, format="json")
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(first.data["amount"], "2000.00")
        self.assertEqual(first.data["phone"], "*******5678")
        self.assertTrue(first.data["stk_accepted"])
        self.assertEqual(MpesaPayment.objects.get(pk=first.data["id"]).stk_response, initiate.return_value)
        initiate.assert_called_once()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_uncertain_stk_outcome_stays_pending_and_is_reused(self, initiate):
        pk = self.booking().data["id"]
        initiate.side_effect = DarajaRequestError(
            "STK Push",
            "STK Push outcome uncertain: submission timed out; do not retry until this attempt is reconciled.",
            True,
        )
        url = f"/api/pay/booking/{pk}/"

        first = self.client.post(url, {"phone": "0712345678"}, format="json")
        second = self.client.post(url, {"phone": "0712345678"}, format="json")

        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data["status"], "uncertain")
        self.assertTrue(first.data["initiation_uncertain"])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["id"], first.data["id"])
        self.assertEqual(MpesaPayment.objects.filter(booking_id=pk).count(), 1)
        initiate.assert_called_once()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_legacy_timeout_without_checkout_id_blocks_retry(self, initiate):
        pk = self.booking().data["id"]
        booking = Booking.objects.get(pk=pk)
        MpesaPayment.objects.create(
            booking=booking,
            phone="254712345678",
            amount=booking.total_price,
            status="failed",
            result_description="HTTPSConnectionPool: Read timed out. (read timeout=30)",
        )

        response = self.client.post(f"/api/pay/booking/{pk}/", {"phone": "0712345678"}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.data["outcome_uncertain"])
        self.assertEqual(MpesaPayment.objects.filter(booking_id=pk).count(), 1)
        initiate.assert_not_called()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_invalid_callback_configuration_blocks_before_creating_payment(self, initiate):
        with override_settings(MPESA_CALLBACK_URL_VALID=False):
            pk = self.booking().data["id"]
            response = self.client.post(f"/api/pay/booking/{pk}/", {"phone": "0712345678"}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(MpesaPayment.objects.filter(booking_id=pk).exists())
        initiate.assert_not_called()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_phone_validation_and_non_integer_amount_are_rejected_before_stk(self, initiate):
        pk = self.booking().data["id"]
        response = self.client.post(f"/api/pay/booking/{pk}/", {"phone": "abc0712345678"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MpesaPayment.objects.filter(booking_id=pk).exists())

        fractional_house = House.objects.create(
            name="Fractional Nest",
            location="Nairobi",
            bedrooms=1,
            price_per_night="1000.25",
        )
        fractional = self.client.post(
            "/api/bookings/",
            {"house": fractional_house.pk, "check_in": str(self.start), "check_out": str(self.start + timedelta(days=2))},
            format="json",
        )
        response = self.client.post(
            f"/api/pay/booking/{fractional.data['id']}/",
            {"phone": "+254712345678"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        initiate.assert_not_called()

    @patch("plots.api.api_views.initiate_stk_push")
    def test_accepted_response_missing_identifiers_is_uncertain_and_not_retried(self, initiate):
        pk = self.booking().data["id"]
        initiate.return_value = {"ResponseCode": "0", "CheckoutRequestID": "checkout-only"}
        url = f"/api/pay/booking/{pk}/"

        first = self.client.post(url, {"phone": "0712345678"}, format="json")
        second = self.client.post(url, {"phone": "0712345678"}, format="json")

        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data["status"], "uncertain")
        self.assertFalse(first.data["stk_accepted"])
        self.assertEqual(second.data["id"], first.data["id"])
        initiate.assert_called_once()

    @patch("plots.api.api_views.query_stk_push")
    @patch("plots.api.api_views.initiate_stk_push")
    def test_query_success_marks_only_matching_booking_paid(self, initiate, query):
        pk = self.booking().data["id"]
        initiate.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-query",
            "MerchantRequestID": "merchant-query",
        }
        started = self.client.post(f"/api/pay/booking/{pk}/", {"phone": "0712345678"}, format="json")
        payment = MpesaPayment.objects.get(pk=started.data["id"])
        query.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-query",
            "MerchantRequestID": "merchant-query",
            "ResultCode": "0",
            "ResultDesc": "The service request is processed successfully.",
        }

        status = self.client.get(f"/api/payments/{payment.pk}/")

        self.assertEqual(status.data["status"], "success")
        self.assertTrue(Booking.objects.get(pk=pk).paid)
        self.assertIsNone(status.data["receipt"])
        query.assert_called_once_with("checkout-query")

    @patch("plots.api.api_views.query_stk_push")
    def test_query_does_not_confirm_ambiguous_result_and_cancels_known_cancellation(self, query):
        booking_pk = self.booking().data["id"]
        booking = Booking.objects.get(pk=booking_pk)
        payment = MpesaPayment.objects.create(
            booking=booking, phone="254712345678", amount=booking.total_price,
            checkout_request_id="checkout-query-2", merchant_request_id="merchant-query-2",
        )
        query.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-query-2",
            "MerchantRequestID": "merchant-query-2",
        }
        self.assertEqual(self.client.get(f"/api/payments/{payment.pk}/").data["status"], "pending")
        payment.refresh_from_db()
        self.assertFalse(booking.paid)

        payment.last_query_at = None
        payment.save(update_fields=["last_query_at"])
        query.return_value["ResultCode"] = "1032"
        query.return_value["ResultDesc"] = "Request cancelled by user"
        self.assertEqual(self.client.get(f"/api/payments/{payment.pk}/").data["status"], "cancelled")
        self.assertFalse(Booking.objects.get(pk=booking_pk).paid)

    @patch("plots.api.api_views.query_stk_push")
    def test_status_query_requires_checkout_id_and_payment_ownership(self, query):
        booking_pk = self.booking().data["id"]
        booking = Booking.objects.get(pk=booking_pk)
        payment = MpesaPayment.objects.create(
            booking=booking, phone="254712345678", amount=booking.total_price,
            status="uncertain",
        )
        status = self.client.get(f"/api/payments/{payment.pk}/")
        self.assertEqual(status.data["status"], "uncertain")
        query.assert_not_called()

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/payments/{payment.pk}/").status_code, 404)

    @patch("plots.api.api_views.query_stk_push")
    def test_failed_and_malformed_callbacks_never_mark_booking_paid(self, query):
        booking_pk = self.booking().data["id"]
        booking = Booking.objects.get(pk=booking_pk)
        payment = MpesaPayment.objects.create(
            booking=booking, phone="254712345678", amount=booking.total_price,
            checkout_request_id="checkout-failed", merchant_request_id="merchant-failed",
        )
        malformed = self.client.post("/api/mpesa/callback/", {"Body": []}, format="json")
        self.assertEqual(malformed.status_code, 400)
        query.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-failed",
            "MerchantRequestID": "merchant-failed",
            "ResultCode": "1",
            "ResultDesc": "Insufficient balance",
        }
        failed = self.client.post(
            "/api/mpesa/callback/",
            {"Body": {"stkCallback": {
                "CheckoutRequestID": "checkout-failed",
                "MerchantRequestID": "merchant-failed",
                "ResultCode": 1,
                "ResultDesc": "Insufficient balance",
            }}},
            format="json",
        )
        self.assertEqual(failed.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        self.assertFalse(Booking.objects.get(pk=booking_pk).paid)

        unknown = self.client.post(
            "/api/mpesa/callback/",
            {"Body": {"stkCallback": {
                "CheckoutRequestID": "unknown-checkout",
                "MerchantRequestID": "unknown-merchant",
                "ResultCode": 1,
                "ResultDesc": "Failed",
            }}},
            format="json",
        )
        self.assertEqual(unknown.status_code, 202)
        self.assertTrue(MpesaPayment.objects.filter(pk=payment.pk).exists())

    @patch("plots.api.api_views.query_stk_push")
    def test_unverified_callback_cannot_mark_payment_successful(self, query):
        booking_pk = self.booking().data["id"]
        booking = Booking.objects.get(pk=booking_pk)
        payment = MpesaPayment.objects.create(
            booking=booking, phone="254712345678", amount=booking.total_price,
            checkout_request_id="checkout-spoof", merchant_request_id="merchant-spoof",
        )
        query.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-spoof",
            "MerchantRequestID": "merchant-spoof",
            "ResultCode": "1",
            "ResultDesc": "Insufficient balance",
        }
        response = self.client.post(
            "/api/mpesa/callback/",
            {"Body": {"stkCallback": {
                "CheckoutRequestID": "checkout-spoof",
                "MerchantRequestID": "merchant-spoof",
                "ResultCode": 0,
                "CallbackMetadata": {"Item": [
                    {"Name": "Amount", "Value": int(payment.amount)},
                    {"Name": "PhoneNumber", "Value": 254712345678},
                    {"Name": "MpesaReceiptNumber", "Value": "FAKE123"},
                ]},
            }}},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(Booking.objects.get(pk=booking_pk).paid)

    @patch("plots.api.api_views.initiate_stk_push")
    def test_long_stay_period_still_uses_its_own_amount_and_booking(self, initiate):
        response = self.booking(self.start, self.start + timedelta(days=65))
        period = PaymentPeriod.objects.get(booking_id=response.data["id"], number=1)
        initiate.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "period-checkout",
            "MerchantRequestID": "period-merchant",
        }
        started = self.client.post(
            f"/api/pay/period/{period.pk}/",
            {"phone": "0112345678"},
            format="json",
        )
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.data["amount"], str(period.amount))
        self.assertEqual(started.data["phone"], "*******5678")
        self.assertEqual(MpesaPayment.objects.get(pk=started.data["id"]).period_id, period.pk)

    @patch("plots.api.api_views.query_stk_push")
    def test_successful_callback_pays_only_the_matching_period(self, query):
        created = self.booking(self.start, self.start + timedelta(days=65))
        booking = Booking.objects.get(pk=created.data["id"])
        period = booking.periods.get(number=1)
        other_period = booking.periods.get(number=2)
        payment = MpesaPayment.objects.create(
            period=period,
            phone="254712345678",
            amount=period.amount,
            checkout_request_id="period-checkout-success",
            merchant_request_id="period-merchant-success",
        )
        query.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": payment.checkout_request_id,
            "MerchantRequestID": payment.merchant_request_id,
            "ResultCode": "0",
            "ResultDesc": "The service request is processed successfully.",
        }
        callback = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": payment.checkout_request_id,
                    "MerchantRequestID": payment.merchant_request_id,
                    "ResultCode": 0,
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": int(period.amount)},
                            {"Name": "PhoneNumber", "Value": 254712345678},
                            {"Name": "MpesaReceiptNumber", "Value": "PERIOD123"},
                        ],
                    },
                },
            },
        }

        response = self.client.post("/api/mpesa/callback/", callback, format="json")

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        period.refresh_from_db()
        other_period.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(payment.status, "success")
        self.assertEqual(payment.receipt, "PERIOD123")
        self.assertTrue(period.paid)
        self.assertIsNotNone(period.paid_at)
        self.assertFalse(other_period.paid)
        self.assertFalse(booking.paid)
        query.assert_called_once_with(payment.checkout_request_id)

    @patch("plots.api.api_views.query_stk_push")
    @patch("plots.api.api_views.initiate_stk_push")
    def test_callback_receipt_and_ownership(self, initiate, query):
        pk = self.booking().data["id"]
        initiate.return_value = {"ResponseCode": "0", "CheckoutRequestID": "checkout-2", "MerchantRequestID": "merchant-2"}
        started = self.client.post(f"/api/pay/booking/{pk}/", {"phone": "0712345678"}, format="json")
        payment = MpesaPayment.objects.get(pk=started.data["id"])
        query.return_value = {
            "ResponseCode": "0",
            "CheckoutRequestID": "checkout-2",
            "MerchantRequestID": "merchant-2",
            "ResultCode": "0",
            "ResultDesc": "The service request is processed successfully.",
        }
        callback = {"Body": {"stkCallback": {"CheckoutRequestID": "checkout-2", "MerchantRequestID": "merchant-2", "ResultCode": 0, "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": int(payment.amount)}, {"Name": "PhoneNumber", "Value": 254712345678}, {"Name": "MpesaReceiptNumber", "Value": "QAB123XYZ"}]}}}}
        self.client.post("/api/mpesa/callback/", callback, format="json")
        self.client.post("/api/mpesa/callback/", callback, format="json")
        result = self.client.get(f"/api/payments/{payment.pk}/")
        self.assertEqual(result.data["status"], "success")
        self.assertEqual(result.data["receipt"], "QAB123XYZ")
        self.assertTrue(Booking.objects.get(pk=pk).paid)
        query.assert_called_once_with("checkout-2")
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

    def test_manager_rejects_fractional_or_out_of_range_apartment_prices(self):
        self.auth(self.manager)
        for price in ("1000.25", "0", "5000"):
            with self.subTest(price=price):
                response = self.client.post(
                    "/api/manager/apartments/",
                    {
                        "name": f"Invalid {price}",
                        "location": "Nairobi",
                        "bedrooms": 1,
                        "price_per_night": price,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

        valid = self.client.post(
            "/api/manager/apartments/",
            {
                "name": "Valid upper bound",
                "location": "Nairobi",
                "bedrooms": 1,
                "price_per_night": "4999",
            },
            format="json",
        )
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(Decimal(valid.data["price_per_night"]), Decimal("4999"))

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
