from django.contrib import admin
from .models import (House, Booking, BookingNotification, Review,
                     Announcement, Favorite, LoginEvent, HousePhoto,
                     ManagerProfile, ManagerInvitation)

admin.site.register(House)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(BookingNotification)
admin.site.register(Announcement)
admin.site.register(Favorite)
admin.site.register(LoginEvent)
admin.site.register(HousePhoto)
admin.site.register(ManagerProfile)
admin.site.register(ManagerInvitation)
