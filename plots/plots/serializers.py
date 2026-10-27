from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from .models import House, Booking, PaymentPeriod

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

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