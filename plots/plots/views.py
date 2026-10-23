from datetime import date, timedelta

from django.shortcuts import render , redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import Http404
from django.views.decorators.http import require_POST
from .forms import BookingForm, ReviewForm

DUMMY_HOUSES = [
    {"id": 1, "name": "Sunset Villa", "location": "Nairobi", "bedrooms": 4,
     "price_per_night": 120, "description": "Spacious and bright.", "avg_rating": 4.5, "review_count": 8},
    {"id": 2, "name": "City Loft", "location": "Nairobi", "bedrooms": 1,
     "price_per_night": 50, "description": "Close to everything.", "avg_rating": None, "review_count": 0},
    {"id": 3, "name": "Garden House", "location": "Karuri", "bedrooms": 3,
     "price_per_night": 90, "description": "Quiet with a garden.", "avg_rating": 4.0, "review_count": 3},
]

DEFAULT_BOOKINGS = [
    {"id": 1, "house_id": 2, "house": {"id": 2, "name": "City Loft"}, "check_in": "2026-10-01", "check_out": "2026-10-05",
     "nights": 4, "total_price": 200, "status": "confirmed", "is_long": False,
     "paid": False, "has_review": False, "can_review": True},
    {"id": 2, "house_id": 1, "house": {"id": 1, "name": "Sunset Villa"}, "check_in": "2026-09-01", "check_out": "2026-12-01",
     "nights": 91, "total_price": 10920, "status": "confirmed", "is_long": True,
     "unpaid_count": 2},
]


def _parse_iso_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _find_conflicting_houses(request, check_in, check_out):
    conflicts = set()
    bookings = list(DEFAULT_BOOKINGS)
    bookings.extend(request.session.get("created_bookings", []))

    for booking in bookings:
        if booking.get("status") == "cancelled":
            continue

        booking_check_in = _parse_iso_date(booking.get("check_in"))
        booking_check_out = _parse_iso_date(booking.get("check_out"))
        if booking_check_in is None or booking_check_out is None:
            continue

        if booking_check_in < check_out and check_in < booking_check_out:
            house_id = booking.get("house_id")
            if house_id is None:
                house = booking.get("house") or {}
                house_id = house.get("id")
            if house_id is not None:
                conflicts.add(int(house_id))

    return conflicts


def landing(request):
    return render(request , "landing.html")

def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your account has been created. You can now log in.")
        return redirect("login")
    return render(request , "accounts/signup.html" , {"form" : form})
def dashboard(request):
    context = {    "due_count": 2,
        "announcements": [
            {"title": "Water maintenance", "message": "Water will be off Friday 9am to 12pm.", "created_at": None},
            {"title": "New listing", "message": "Hilltop Retreat is now available.", "created_at": None},
        ],
    }
    return render(request , "dashboard.html" , context)
def house_list(request):
    check_in_raw = request.GET.get("check_in")
    check_out_raw = request.GET.get("check_out")
    check_in = _parse_iso_date(check_in_raw)
    check_out = _parse_iso_date(check_out_raw)
    houses = DUMMY_HOUSES

    if check_in and check_out and check_in < check_out:
        unavailable_houses = _find_conflicting_houses(request, check_in, check_out)
        houses = [house for house in DUMMY_HOUSES if house["id"] not in unavailable_houses]

    return render(request , "bookings/houses.html" , {
        "houses": houses,
        "favs":set(request.session.get("favorite_ids", [])),
        "searched":bool(check_in_raw or check_out_raw),
        "check_in": check_in_raw or "",
        "check_out": check_out_raw or "",
    })
def book(request):
    form = BookingForm(
        request.POST or None,
        houses=DUMMY_HOUSES,
        initial={
            "house": request.GET.get("house"),
            "check_in": request.GET.get("check_in"),
            "check_out": request.GET.get("check_out"),
        },
    )
    if request.method == "POST" and form.is_valid():
        house = next(h for h in DUMMY_HOUSES if str(h["id"]) == form.cleaned_data["house"])
        nights = (form.cleaned_data["check_out"] - form.cleaned_data["check_in"]).days
        bookings = request.session.get("created_bookings", [])
        booking_id = max((b["id"] for b in bookings), default=99) + 1
        bookings.append({
            "id": booking_id,
            "house_id": house["id"],
            "house": {"id": house["id"], "name": house["name"]},
            "check_in": form.cleaned_data["check_in"].isoformat(),
            "check_out": form.cleaned_data["check_out"].isoformat(),
            "nights": nights,
            "total_price": nights * house["price_per_night"],
            "price_per_night": house["price_per_night"],
            "status": "confirmed",
            "is_long": nights > 30,
            "paid": False,
            "has_review": False,
            "can_review": form.cleaned_data["check_out"] <= date.today(),
            "unpaid_count": (nights + 29) // 30 if nights > 30 else 0,
        })
        request.session["created_bookings"] = bookings
        messages.success(request, "Your booking has been created.")
        return redirect("my_bookings")
    return render(request, "bookings/book.html", {"form": form})
def my_bookings(request):
    bookings = [
        {"id": 1, "house_id": 2, "house": {"id": 2, "name": "City Loft"}, "check_in": "2026-10-01", "check_out": "2026-10-05",
        "nights": 4, "total_price": 200, "status": "confirmed", "is_long": False,
        "paid": False, "has_review": False, "can_review": True},
        {"id": 2, "house_id": 1, "house": {"id": 1, "name": "Sunset Villa"}, "check_in": "2026-09-01", "check_out": "2026-12-01",
        "nights": 91, "total_price": 10920, "status": "confirmed", "is_long": True,
        "unpaid_count": 2},
    ]
    overrides = request.session.get("booking_overrides", {})
    bookings = [
        {**booking, **overrides.get(str(booking["id"]), {})}
        for booking in bookings
    ]
    bookings += request.session.get("created_bookings", [])
    reviews = request.session.get("reviews", {})
    for booking in bookings:
        if f'booking-{booking["id"]}' in reviews:
            booking["has_review"] = True
    return render(request , "bookings/my_bookings.html" , {"bookings" : bookings})
def booking_card(request , pk):
    bookings = request.session.get("created_bookings", [])
    booking = next((b for b in bookings if b["id"] == pk), None)
    if booking:
        check_out = date.fromisoformat(booking["check_out"])
        start = date.fromisoformat(booking["check_in"])
        periods = []
        reviews = request.session.get("reviews", {})
        paid_periods = booking.get("paid_periods", [])
        while start < check_out:
            end = min(start + timedelta(days=30), check_out)
            number = len(periods) + 1
            periods.append({
                "id": number,
                "number": number,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "amount": (end - start).days * booking["price_per_night"],
                "paid": number in paid_periods,
                "has_review": f"period-{pk}-{number}" in reviews,
                "can_review": number in paid_periods and end <= date.today(),
            })
            start = end
        paid_total = sum(p["amount"] for p in periods if p["paid"])
        total_price = booking["total_price"]
        house_name = booking["house"]["name"]
        check_in = booking["check_in"]
        checkout_text = booking["check_out"]
    elif pk == 2:
        periods = [
        {"id": 1, "number": 1, "start": "2026-09-01", "end": "2026-10-01", "amount": 3600,
         "paid": True, "has_review": False, "can_review": True},
        {"id": 2, "number": 2, "start": "2026-10-01", "end": "2026-10-31", "amount": 3600,
         "paid": False, "has_review": False, "can_review": False},
        {"id": 3, "number": 3, "start": "2026-10-31", "end": "2026-12-01", "amount": 3720,
         "paid": False, "has_review": False, "can_review": False}
        ]
        paid_periods = request.session.get("paid_periods", {}).get(str(pk), [])
        for period in periods:
            period["paid"] = period["number"] in paid_periods or period["paid"]
        paid_total = sum(p["amount"] for p in periods if p["paid"])
        total_price = 10920
        house_name = "Sunset Villa"
        check_in = "2026-09-01"
        checkout_text = "2026-12-01"
    else:
        raise Http404("Booking not found.")
    return render(request , "bookings/booking_card.html" , {
         "booking": {"id": pk, "house": {"name": house_name},
                    "check_in": check_in, "check_out": checkout_text, "total_price": total_price},
        "periods": periods, "paid_total": paid_total, "outstanding": total_price - paid_total,

    })
def favourites(request):
    favorite_ids = set(request.session.get("favorite_ids", []))
    houses = [house for house in DUMMY_HOUSES if house["id"] in favorite_ids]
    return render(request , "bookings/fav.html" , {"houses" : houses})

def review_booking(request, pk):
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reviews = request.session.get("reviews", {})
        reviews[f"booking-{pk}"] = form.cleaned_data
        request.session["reviews"] = reviews
        messages.success(request, "Your review has been saved.")
        return redirect("my_bookings")
    return render(request, "bookings/review.html",
                  {"form": form, "target_label": f"Booking {pk}"})
def review_period(request, booking_pk, period_pk):
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reviews = request.session.get("reviews", {})
        reviews[f"period-{booking_pk}-{period_pk}"] = form.cleaned_data
        request.session["reviews"] = reviews
        messages.success(request, "Your review has been saved.")
        return redirect("booking_card", pk=booking_pk)
    return render(request, "bookings/review.html",
                  {"form": form, "target_label": f"Payment period {period_pk}"})
@require_POST
def cancel_booking(request, pk):
    overrides = request.session.get("booking_overrides", {})
    overrides.setdefault(str(pk), {})["status"] = "cancelled"
    request.session["booking_overrides"] = overrides
    bookings = request.session.get("created_bookings", [])
    for booking in bookings:
        if booking["id"] == pk:
            booking["status"] = "cancelled"
    request.session["created_bookings"] = bookings
    return redirect("my_bookings")


@require_POST
def pay_booking(request, pk):
    overrides = request.session.get("booking_overrides", {})
    overrides.setdefault(str(pk), {})["paid"] = True
    request.session["booking_overrides"] = overrides
    bookings = request.session.get("created_bookings", [])
    for booking in bookings:
        if booking["id"] == pk:
            booking["paid"] = True
    request.session["created_bookings"] = bookings
    return redirect("my_bookings")


@require_POST
def pay_period(request, booking_pk, period_pk):
    bookings = request.session.get("created_bookings", [])
    booking = next((b for b in bookings if b["id"] == booking_pk), None)
    if booking:
        paid_periods = booking.setdefault("paid_periods", [])
        if period_pk not in paid_periods:
            paid_periods.append(period_pk)
        request.session["created_bookings"] = bookings
    else:
        paid_periods = request.session.get("paid_periods", {})
        booking_periods = paid_periods.setdefault(str(booking_pk), [])
        if period_pk not in booking_periods:
            booking_periods.append(period_pk)
        request.session["paid_periods"] = paid_periods
    return redirect("booking_card", pk=booking_pk)


@require_POST
def toggle_favourite(request, pk):
    favorite_ids = set(request.session.get("favorite_ids", []))
    if pk in favorite_ids:
        favorite_ids.remove(pk)
    else:
        favorite_ids.add(pk)
    request.session["favorite_ids"] = sorted(favorite_ids)
    return redirect("houses")
def analytics(request):
    return render(request, "analytics/dashboard.html", {
        "total_revenue": 12500, "total_bookings": 60, "total_users": 10,
        "outstanding": 7320, "charts": [],
    })