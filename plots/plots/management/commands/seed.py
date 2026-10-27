import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from plots.models import (House, Booking, PaymentPeriod, Review,
                          Announcement, Favorite, LoginEvent)

User = get_user_model()


class Command(BaseCommand):
    help = "Generate demo guests, apartments, bookings, payments, reviews and logins"

    def make_booking(self, user, house, cin, cout, status="confirmed", created_at=None):
        today = timezone.localdate()
        b = Booking.objects.create(
            user=user, house=house, check_in=cin, check_out=cout, status=status,
            total_price=(cout - cin).days * house.price_per_night,
            created_at=created_at or timezone.now(),
        )
        if b.is_long:
            b.create_periods()
            for p in b.periods.all():
                if p.end <= today:                      # finished periods are paid
                    p.paid, p.paid_at = True, timezone.now()
                    p.save()
        elif cout <= today and status == "confirmed":   # finished short stays are paid
            b.paid, b.paid_at = True, timezone.now()
            b.save()
        return b

    def handle(self, *args, **opts):
        now = timezone.now()
        today = timezone.localdate()
        d = timedelta

        # Wipe old demo data (only users named guest1..guest10)
        User.objects.filter(username__startswith="guest").delete()

        houses = []
        for name, loc, beds, price in [
            ("Sunset Villa", "Nairobi", 4, "120"), ("Lakeview Cottage", "Naivasha", 2, "75"),
            ("City Loft", "Nairobi", 1, "50"), ("Garden House", "Karuri", 3, "90"),
            ("Hilltop Retreat", "Limuru", 5, "150"), ("Cosy Studio", "Thika", 1, "35"),
        ]:
            h, _ = House.objects.get_or_create(name=name, defaults=dict(
                location=loc, bedrooms=beds, price_per_night=Decimal(price),
                description="Comfortable, clean and ready to move in."))
            houses.append(h)

        users = []
        for i in range(1, 11):
            u = User.objects.create_user(username=f"guest{i}", password="pass12345")
            u.date_joined = now - d(days=random.randint(1, 30))
            u.save()
            users.append(u)
        demo = users[0]   # guest1 gets one booking for every review/payment case

        # ---- Demo bookings for guest1 (cover every branch of the rules) ----
        self.make_booking(demo, houses[0], today - d(days=10), today - d(days=5))    # finished short: can review
        self.make_booking(demo, houses[1], today - d(days=2), today + d(days=3))     # ongoing short: cannot review
        self.make_booking(demo, houses[2], today - d(days=35), today + d(days=55))   # long, 35 days in: period 1 reviewable
        self.make_booking(demo, houses[3], today - d(days=20), today + d(days=70))   # long, 20 days in: nothing yet

        # ---- Random history for the other guests ----
        made = 0
        for _ in range(400):
            if made >= 55:
                break
            house = random.choice(houses)
            cin = today - d(days=random.randint(0, 29))
            nights = random.choice([2, 3, 4, 5, 7, 10, 40, 60])
            cout = cin + d(days=nights)
            if not house.is_free(cin, cout):
                continue
            self.make_booking(
                random.choice(users[1:]), house, cin, cout,
                status=random.choice(["confirmed"] * 5 + ["cancelled"]),
                created_at=now - d(days=random.randint(0, 29)),
            )
            made += 1

        # ---- Reviews (skip guest1 so the demo buttons still work) ----
        comments = ["Great place!", "Clean and quiet.", "Good value.", "Would stay again.", ""]
        for b in Booking.objects.filter(status="confirmed").exclude(user=demo):
            if b.is_long:
                for p in b.periods.filter(paid=True):
                    if p.end <= today and random.random() < 0.6:
                        Review.objects.create(user=b.user, house=b.house, booking=b, period=p,
                                              rating=random.choice([3, 4, 4, 5, 5]),
                                              comment=random.choice(comments))
            elif b.check_out <= today and random.random() < 0.6:
                Review.objects.create(user=b.user, house=b.house, booking=b,
                                      rating=random.choice([3, 4, 4, 5, 5]),
                                      comment=random.choice(comments))

        # ---- Logins, favorites, announcements ----
        LoginEvent.objects.bulk_create([
            LoginEvent(user=random.choice(users),
                       timestamp=now - d(days=random.randint(0, 29), hours=random.randint(0, 23)))
            for _ in range(200)
        ])
        for _ in range(25):
            Favorite.objects.get_or_create(user=random.choice(users), house=random.choice(houses))

        if not Announcement.objects.exists():
            Announcement.objects.create(
                title="Welcome to BookIt",
                message="Thanks for staying with us. Reviews are open after your stay.")

        self.stdout.write(self.style.SUCCESS(
            "Seeded. Log in as guest1 / pass12345 to demo every case."))