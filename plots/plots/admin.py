from django.contrib import admin
from .models import (House, Booking, PaymentPeriod, Review,
                     Announcement, Favorite, LoginEvent, HousePhoto,
                     ManagerProfile, ManagerInvitation, MpesaPayment,
                     MpesaCallbackEvent)

admin.site.register(House)
admin.site.register(Booking)
admin.site.register(PaymentPeriod)
admin.site.register(Review)
admin.site.register(Announcement)
admin.site.register(Favorite)
admin.site.register(LoginEvent)
admin.site.register(HousePhoto)
admin.site.register(ManagerProfile)
admin.site.register(ManagerInvitation)
admin.site.register(MpesaPayment)
admin.site.register(MpesaCallbackEvent)
