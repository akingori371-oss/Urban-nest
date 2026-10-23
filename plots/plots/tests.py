from django.test import TestCase
from django.urls import reverse

from .forms import BookingForm


class BookingAvailabilityTests(TestCase):
    def test_house_list_filters_unavailable_dates(self):
        response = self.client.get(
            reverse("houses"),
            {"check_in": "2026-10-02", "check_out": "2026-10-04"},
        )

        self.assertEqual(response.status_code, 200)
        house_ids = [house["id"] for house in response.context["houses"]]
        self.assertEqual(house_ids, [3])

    def test_booking_form_allows_optional_houses_argument(self):
        form = BookingForm()
        self.assertEqual(form.fields["house"].choices, [])
