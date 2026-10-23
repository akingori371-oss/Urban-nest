from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class House(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)

    def is_free(self, check_in, check_out):
        return not self.booking_set.filter(
            status="confirmed", check_in__lt=check_out, check_out__gt=check_in
        ).exists()

    def __str__(self):
        return self.name


class Booking(models.Model):
    STATUS = [("confirmed", "Confirmed"), ("cancelled", "Cancelled")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="confirmed")
    paid = models.BooleanField(default=False)          # used for short stays only
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    @property
    def is_long(self):
        return self.nights > 30

    @property
    def unpaid_count(self):
        return self.periods.filter(paid=False).count()

    @property
    def has_review(self):
        return self.reviews.filter(period__isnull=True).exists()

    @property
    def can_review(self):
        # short stays: unlocks at check-out
        return (not self.is_long and self.status == "confirmed"
                and self.check_out <= timezone.localdate() and not self.has_review)

    def create_periods(self):
        """Split a long stay into 30-day payment periods."""
        start, number = self.check_in, 1
        while start < self.check_out:
            end = min(start + timedelta(days=30), self.check_out)
            PaymentPeriod.objects.create(
                booking=self, number=number, start=start, end=end,
                amount=(end - start).days * self.house.price_per_night,
            )
            start, number = end, number + 1

    def __str__(self):
        return f"{self.user} - {self.house} ({self.check_in} to {self.check_out})"


class PaymentPeriod(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="periods")
    number = models.PositiveSmallIntegerField()
    start = models.DateField()
    end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["number"]

    @property
    def has_review(self):
        return self.reviews.exists()

    @property
    def can_review(self):
        # long stays: period must be over AND paid
        return self.paid and self.end <= timezone.localdate() and not self.has_review

    def __str__(self):
        return f"{self.booking} - period {self.number}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="reviews")
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="reviews")
    period = models.ForeignKey(PaymentPeriod, on_delete=models.CASCADE, null=True, blank=True,
                               related_name="reviews")   # empty for short stays
    rating = models.PositiveSmallIntegerField(choices=[(i, f"{i} stars") for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["booking"], condition=models.Q(period__isnull=True),
                                    name="one_review_per_short_booking"),
            models.UniqueConstraint(fields=["period"], condition=models.Q(period__isnull=False),
                                    name="one_review_per_period"),
        ]


class Announcement(models.Model):
    title = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "house")