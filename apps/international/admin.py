from django.contrib import admin
from apps.international.models import *
# Register your models here.


admin.site.register(Country)
admin.site.register(City)
admin.site.register(InternationalPolicy)
admin.site.register(InternationalOrders)

