from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from ..models import (Announcement, Booking, House, HousePhoto, ManagerInvitation,
                      MpesaPayment, PaymentPeriod, Review)

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, data):
        return User.objects.create_user(**data)


class HouseSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = House
        fields = ["id", "name", "location", "bedrooms", "price_per_night",
                  "description", "avg_rating", "review_count"]


class ReviewSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "comment", "created_at"]


class HouseDetailSerializer(HouseSerializer):
    reviews = ReviewSummarySerializer(many=True, read_only=True)
    availability = serializers.SerializerMethodField()

    class Meta(HouseSerializer.Meta):
        fields = HouseSerializer.Meta.fields + ["reviews", "availability"]

    def get_availability(self, house):
        request = self.context.get("request")
        if request is None:
            return None
        check_in = request.query_params.get("check_in")
        check_out = request.query_params.get("check_out")
        if not check_in or not check_out:
            return None
        from django.utils.dateparse import parse_date
        start, end = parse_date(check_in), parse_date(check_out)
        if start is None or end is None or end <= start:
            return None
        return house.is_free(start, end)


class BookingSerializer(serializers.ModelSerializer):
    house_name = serializers.CharField(source="house.name", read_only=True)
    nights = serializers.IntegerField(read_only=True)
    is_long = serializers.BooleanField(read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "house", "house_name", "check_in", "check_out",
                  "nights", "total_price", "status", "paid", "is_long"]
        read_only_fields = ["total_price", "status", "paid"]

    def validate(self, data):
        if data["check_in"] < timezone.localdate():
            raise serializers.ValidationError("Check-in can't be in the past.")
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError("Check-out must be after check-in.")
        if not data["house"].is_free(data["check_in"], data["check_out"]):
            raise serializers.ValidationError("That apartment is already booked for those dates.")
        return data


class PaymentPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPeriod
        fields = ["id", "number", "start", "end", "amount", "paid"]


class ManagerHouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = House
        fields = ["id", "name", "location", "description", "bedrooms", "price_per_night", "is_active"]


class HousePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HousePhoto
        fields = ["id", "image", "caption", "created_at"]
        read_only_fields = ["id", "created_at"]


class ManagerAnnouncementSerializer(serializers.ModelSerializer):
    recipient_ids = serializers.PrimaryKeyRelatedField(source="recipients", many=True, queryset=User.objects.all(), required=False)

    class Meta:
        model = Announcement
        fields = ["id", "title", "message", "created_at", "is_published", "recipient_ids"]
        read_only_fields = ["id", "created_at"]


class ManagerPaymentSerializer(serializers.ModelSerializer):
    tenant = serializers.SerializerMethodField()
    apartment = serializers.SerializerMethodField()
    booking_id = serializers.IntegerField(read_only=True)
    period_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = MpesaPayment
        fields = ["id", "tenant", "apartment", "booking_id", "period_id", "amount", "phone", "receipt", "status", "result_description", "created_at"]

    def get_tenant(self, obj):
        booking = obj.booking or (obj.period.booking if obj.period_id else None)
        return {"id": booking.user_id, "username": booking.user.username, "email": booking.user.email} if booking else None

    def get_apartment(self, obj):
        booking = obj.booking or (obj.period.booking if obj.period_id else None)
        return {"id": booking.house_id, "name": booking.house.name} if booking else None


class ManagerInvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.CharField(source="invited_by.username", read_only=True, default=None)

    class Meta:
        model = ManagerInvitation
        fields = ["id", "email", "status", "is_main_provision", "created_at", "expires_at", "accepted_at", "invited_by"]
