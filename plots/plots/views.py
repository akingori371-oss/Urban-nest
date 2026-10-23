from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Avg, Count, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date

from .models import House, Booking, PaymentPeriod, Announcement, Favorite


# ---------- Pages ----------

def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    due_count = PaymentPeriod.objects.filter(
        booking__user=request.user, booking__status="confirmed", paid=False
    ).count()
    return render(request, "dashboard.html", {
        "announcements": Announcement.objects.all()[:5],
        "due_count": due_count,
    })


# ---------- Bookings (real data) ----------

@login_required
def house_list(request):
    check_in = parse_date(request.GET.get("check_in") or "")
    check_out = parse_date(request.GET.get("check_out") or "")
    searched = bool(check_in and check_out and check_out > check_in)

    houses = House.objects.annotate(
        avg_rating=Avg("reviews__rating"),
        review_count=Count("reviews"),
    )

    if searched:
        # houses with a confirmed booking that overlaps the dates are busy
        busy = Booking.objects.filter(
            status="confirmed", check_in__lt=check_out, check_out__gt=check_in
        ).values_list("house_id", flat=True)
        houses = houses.exclude(id__in=busy)

    favs = set(Favorite.objects.filter(user=request.user).values_list("house_id", flat=True))

    return render(request, "bookings/houses.html", {
        "houses": houses, "favs": favs, "searched": searched,
        "check_in": request.GET.get("check_in", ""),
        "check_out": request.GET.get("check_out", ""),
    })


@login_required
def my_bookings(request):
    bookings = (Booking.objects.filter(user=request.user)
                .select_related("house").order_by("-check_in"))
    return render(request, "bookings/my_bookings.html", {"bookings": bookings})


@login_required
def booking_card(request, pk):
    # user=request.user means you can only open your own card (others get a 404)
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    periods = booking.periods.all()
    paid_total = periods.filter(paid=True).aggregate(s=Sum("amount"))["s"] or 0
    total = periods.aggregate(s=Sum("amount"))["s"] or 0
    return render(request, "bookings/booking_card.html", {
        "booking": booking, "periods": periods,
        "paid_total": paid_total, "outstanding": total - paid_total,
    })


@login_required
def favorites(request):
    houses = House.objects.filter(favorite__user=request.user)
    return render(request, "bookings/favorites.html", {"houses": houses})


# ---------- Still stubs (next steps) ----------

@login_required
def book(request):
    return render(request, "bookings/book.html", {"form": None})


@login_required
def review_booking(request, pk):
    return render(request, "bookings/review_form.html",
                  {"form": None, "target_label": "Review (coming soon)"})


@login_required
def review_period(request, pk):
    return render(request, "bookings/review_form.html",
                  {"form": None, "target_label": "Review (coming soon)"})


@login_required
def cancel_booking(request, pk):
    return redirect("my_bookings")


@login_required
def pay_booking(request, pk):
    return redirect("my_bookings")


@login_required
def pay_period(request, pk):
    return redirect("my_bookings")


@login_required
def toggle_favorite(request, pk):
    return redirect("houses")


def analytics(request):
    return render(request, "analytics/dashboard.html", {
        "total_revenue": 12500, "total_bookings": 60, "total_users": 10,
        "outstanding": 7320, "charts": [],
    })