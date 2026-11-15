from django.conf import settings
from django.db import models
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
    STATUS = [("pending", "Pending approval"), ("confirmed", "Confirmed"),
              ("rejected", "Rejected"), ("cancelled", "Cancelled")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.PROTECT)
    check_in = models.DateField()
    check_out = models.DateField()
    contact_number = models.CharField(max_length=30, blank=True)
    guest_count = models.PositiveSmallIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="pending", db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    @property
    def has_review(self):
        return self.reviews.exists()

    @property
    def can_review(self):
        return (self.status == "confirmed" and self.check_out <= timezone.localdate()
                and not self.has_review)

    def __str__(self):
        return f"{self.user} - {self.house} ({self.check_in} to {self.check_out})"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="reviews")
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=[(i, f"{i} stars") for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["booking"], name="one_review_per_booking")]


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


class BookingNotification(models.Model):
    KIND = [("booking_received", "Booking received"),
            ("booking_decision", "Booking decision"),
            ("booking_clarification", "Booking clarification"),
            ("manager_booking_request", "Manager booking request")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="booking_notifications")
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32, choices=KIND)
    title = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "booking", "kind"], name="unique_booking_notification")]
        ordering = ["-created_at", "-id"]


class HousePhoto(models.Model):
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="photos")
    image = models.FileField(upload_to="houses/%Y/%m/")
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
