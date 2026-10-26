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
from .models import (House, Booking, PaymentPeriod, Announcement,Favorite, Login)

@login_required
def book(request):
    initial = {k: request.GET.get(k) for k in ("houses" , "check_in" , "check_out")
               if request.GET.get(k)}
    form = Booking(request.POST or None, initial=initial)