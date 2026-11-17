
from django.contrib import admin
from .models import (
    House, Booking, BookingNotification, Review,
    Announcement, Favorite, LoginEvent, HousePhoto,
    ManagerProfile, ManagerInvitation
)


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "county",
        "location",
        "approval_status",
        "is_active",
        "created_at",
    )

    list_filter = (
        "approval_status",
        "is_active",
        "county",
        "property_type",
    )

    search_fields = (
        "name",
        "location",
        "county",
        "owner__username",
        "owner__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "reviewed_at",
    )

    actions = ["approve_houses", "reject_houses"]

    @admin.action(description="Approve selected properties")
    def approve_houses(self, request, queryset):
        queryset.update(
            approval_status="approved",
            reviewed_by=request.user,
        )

    @admin.action(description="Reject selected properties")
    def reject_houses(self, request, queryset):
        queryset.update(
            approval_status="rejected",
            reviewed_by=request.user,
        )


admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(BookingNotification)
admin.site.register(Announcement)
admin.site.register(Favorite)
admin.site.register(LoginEvent)
admin.site.register(HousePhoto)
admin.site.register(ManagerProfile)
admin.site.register(ManagerInvitation)
