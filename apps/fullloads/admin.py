from django.contrib import admin
from apps.fullloads.models import *
# Register your models here.

admin.site.register(VehicleType)
admin.site.register(VehiclePricing)
admin.site.register(DistanceBand)
admin.site.register(WeightTier)
admin.site.register(Booking)
admin.site.register(Surge)
