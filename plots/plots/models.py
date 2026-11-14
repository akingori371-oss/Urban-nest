from datetime import timedelta
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class House(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True, db_index=True)

    def is_free(self, check_in, check_out):
        return not self.booking_set.filter(
            status="confirmed", check_in__lt=check_out, check_out__gt=check_in
        ).exists()

    def __str__(self):
        return self.name


class Booking(models.Model):
    STATUS = [("confirmed", "Confirmed"), ("cancelled", "Cancelled")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.PROTECT)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="confirmed", db_index=True)
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
        """Create 30-day payment periods idempotently for long stays."""
        if not self.is_long:
            return
        start, number = self.check_in, 1
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=self.pk)
            while start < booking.check_out:
                end = min(start + timedelta(days=30), booking.check_out)
                PaymentPeriod.objects.get_or_create(
                    booking=booking,
                    number=number,
                    defaults={
                        "start": start,
                        "end": end,
                        "amount": (end - start).days * booking.house.price_per_night,
                    },
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
        constraints = [
            models.UniqueConstraint(fields=["booking", "number"], name="unique_booking_period_number"),
        ]

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
    is_published = models.BooleanField(default=True, db_index=True)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="targeted_announcements")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "house")

class LoginEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} at {self.timestamp:%Y-%m-%d %H:%M}"        

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    try:
        LoginEvent.objects.create(user=user)
    except Exception:
        pass  # analytics must never block a login


class MpesaPayment(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("review", "Needs review"),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mpesa_payments"
    )

    period = models.ForeignKey(
        PaymentPeriod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mpesa_payments"
    )

    checkout_request_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True
    )

    phone = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=10,
        choices=STATUS,
        default="pending",
        db_index=True,
    )

    receipt = models.CharField(max_length=50, blank=True)
    result_description = models.CharField(max_length=255, blank=True)
    result_code = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(booking__isnull=False, period__isnull=True)
                           | models.Q(booking__isnull=True, period__isnull=False)),
                name="mpesa_payment_exactly_one_target",
            ),
        ]

    def __str__(self):
        return f"M-Pesa {self.checkout_request_id} - {self.status}"


class MpesaCallbackEvent(models.Model):
    """Keep callbacks that race the STK response for later reconciliation."""
    checkout_request_id = models.CharField(max_length=100, unique=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class HousePhoto(models.Model):
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="houses/%Y/%m/")
    caption = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class ManagerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="manager_profile")
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["is_main"], condition=models.Q(is_main=True), name="only_one_main_manager")]

    def __str__(self):
        return f"{self.user.email} ({'main' if self.is_main else 'manager'})"


class ManagerInvitation(models.Model):
    STATUS = [("pending", "Pending"), ("accepted", "Accepted"), ("cancelled", "Cancelled"), ("expired", "Expired")]
    email = models.EmailField(db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending", db_index=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="manager_invitations_sent")
    is_main_provision = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.email} ({self.status})"
