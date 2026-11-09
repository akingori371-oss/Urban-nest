from django.contrib import admin
from .models import (House, Booking, PaymentPeriod, Review,
                     Announcement, Favorite, LoginEvent)

admin.site.register(House)
admin.site.register(Booking)
admin.site.register(PaymentPeriod)
admin.site.register(Review)
admin.site.register(Announcement)
admin.site.register(Favorite)
admin.site.register(LoginEvent)