from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .forms import BookingForm
from .models import (House, Booking, PaymentPeriod, Announcement,Favorite)



def landing(request):
    return render(request, "landing.html")

@login_required
def book(request):
    initial = {k: request.GET.get(k) for k in ("house", "check_in", "check_out")
               if request.GET.get(k)}
    form = BookingForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.total_price = booking.nights * booking.house.price_per_night
            booking.save()
            if booking.is_long:
                booking.create_periods()
        if booking.is_long:
            messages.success(request, "Booked! Your payment card has been issued.")
        else:
            messages.success(request, "Booked! You can pay now or at check-out.")
        return redirect("my_bookings")
    return render(request, "bookings/book.html", {"form": form})


@login_required
@require_POST
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)  # only your own
    booking.status = "cancelled"
    booking.save()
    messages.info(request, "Booking cancelled.")
    return redirect("my_bookings")


@login_required
@require_POST
def pay_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if booking.is_long:
        messages.warning(request, "Long stays are paid per period on the payment card.")
        return redirect("booking_card", pk=booking.pk)
    booking.paid = True
    booking.paid_at = timezone.now()
    booking.save()
    messages.success(request, "Payment recorded.")
    return redirect("my_bookings")


@login_required
@require_POST
def pay_period(request, pk):
    period = get_object_or_404(PaymentPeriod, pk=pk, booking__user=request.user)
    period.paid = True
    period.paid_at = timezone.now()
    period.save()
    messages.success(request, f"Period {period.number} paid.")
    return redirect("booking_card", pk=period.booking_id)


@login_required
@require_POST
def toggle_favorite(request, pk):
    house = get_object_or_404(House, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, house=house)
    if not created:
        fav.delete()
    return redirect("houses")


@login_required
def analytics(request):
    if not request.user.is_superuser:
        raise PermissionDenied  # shows a 403 page to guests

    short_paid = (Booking.objects.filter(status="confirmed", paid=True)
                  .aggregate(s=Sum("total_price"))["s"] or 0)
    periods_paid = (PaymentPeriod.objects.filter(booking__status="confirmed", paid=True)
                    .aggregate(s=Sum("amount"))["s"] or 0)
    periods_due = (PaymentPeriod.objects.filter(booking__status="confirmed", paid=False)
                   .aggregate(s=Sum("amount"))["s"] or 0)
    short_due = (Booking.objects.filter(status="confirmed", paid=False)
                 .exclude(periods__isnull=False)
                 .aggregate(s=Sum("total_price"))["s"] or 0)

    return render(request, "analytics/dashboard.html", {
        "total_revenue": short_paid + periods_paid,
        "total_bookings": Booking.objects.filter(status="confirmed").count(),
        "total_users": request.user.__class__.objects.filter(is_superuser=False).count(),
        "outstanding": periods_due + short_due,
        "charts": [],   # plots come next
    })
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})