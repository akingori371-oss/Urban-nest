from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from ..models import (Announcement, Booking, House, HousePhoto, ManagerInvitation,
                      Review)

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
    photos = serializers.SerializerMethodField()

    class Meta:
        model = House
        fields = [
            "id",
            "name",
            "county",
            "location",
            "property_type",
            "description",
            "bedrooms",
            "price_per_night",
            "amenities",
            "avg_rating",
            "review_count",
            "photos",
        ]

    def get_photos(self, house):
        request = self.context.get("request")
        photos = house.photos.all()[:5]

        return [
            {
                "id": p.id,
                "image": request.build_absolute_uri(p.image.url) if request else p.image.url,
                "caption": p.caption,
            }
            for p in photos
        ]


class HouseSubmissionSerializer(serializers.ModelSerializer):
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )

    class Meta:
        model = House
        fields = [
            "id",
            "name",
            "county",
            "location",
            "property_type",
            "description",
            "bedrooms",
            "price_per_night",
            "amenities",
            "approval_status",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "approval_status",
            "is_active",
            "created_at",
        ]

    def validate_bedrooms(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "A property must have at least one bedroom."
            )
        return value

    def validate_price_per_night(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price per night must be greater than zero."
            )
        return value

    def validate_county(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Please provide the county."
            )

        return value

    def create(self, validated_data):
        request = self.context["request"]

        return House.objects.create(
            **validated_data,
            owner=request.user,
            approval_status="pending",
            is_active=True,
        )




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
    contact_number = serializers.CharField(required=True, max_length=30, allow_blank=False)
    guest_count = serializers.IntegerField(required=True, min_value=1, max_value=30)

    class Meta:
        model = Booking
        fields = ["id", "house", "house_name", "check_in", "check_out",
                  "contact_number", "guest_count", "nights", "total_price",
                  "status", "created_at"]
        read_only_fields = ["total_price", "status", "created_at"]

    def validate_house(self, value):
        if not value.is_active:
            raise serializers.ValidationError("This apartment is not currently available for booking.")
        return value

    def validate(self, data):
        if data["check_in"] < timezone.localdate():
            raise serializers.ValidationError("Check-in can't be in the past.")
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError("Check-out must be after check-in.")
        contact = data.get("contact_number", "").strip()
        data["contact_number"] = contact
        return data


class BookingClarificationSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)


class ManagerHouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = House
        fields = ["id", "name", "location", "description", "bedrooms", "price_per_night", "is_active"]

    def validate_bedrooms(self, value):
        is_demo_compact_type = bool(
            self.instance
            and self.instance.description.startswith("[[URBAN_NEST_DEMO|")
            and ("|TYPE=Studio|" in self.instance.description or "|TYPE=Bedsitter|" in self.instance.description)
        )
        if value < 1 and not (value == 0 and is_demo_compact_type):
            raise serializers.ValidationError("An apartment must have at least one bedroom.")
        return value

    def validate_price_per_night(self, value):
        if value != value.to_integral_value() or value < 1 or value >= 5000:
            raise serializers.ValidationError(
                "Nightly price must be a whole number between KSh 1 and KSh 4,999."
            )
        return value


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


class ManagerInvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.CharField(source="invited_by.username", read_only=True, default=None)

    class Meta:
        model = ManagerInvitation
        fields = ["id", "email", "status", "is_main_provision", "created_at", "expires_at", "accepted_at", "invited_by"]
