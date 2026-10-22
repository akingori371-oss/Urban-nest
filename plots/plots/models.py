# from datetime import timedelta
# from django.conf import settings
# from django.db import models
# from django.utils import timezone

# class House(models.Model):
#     name = models.CharField(max_length=100)
#     location = models.CharField(max_length=100)
#     description = models.TextField(blank=True)
#     bedrooms = models.PositiveSmallIntegerField(default=1)
#     price_per_night = models.DecimalField(max_digits=8, decimal_places=2)

#     def is_free(self,check_in,check_out):
#         return not self.booking_set.filter(
#             status="confirmed" , check_in=check_out
#         )