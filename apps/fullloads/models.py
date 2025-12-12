import random
import string
import uuid
from django.db import models
from apps.accounts.models import Office, User
from django.utils.translation import gettext_lazy as _
from geopy.distance import geodesic
# Create your models here.



class VehicleType(models.Model):
    name = models.CharField(max_length=255)
    weight = models.PositiveIntegerField(null=True)
    description = models.TextField()

    class Meta:
        ordering = ["weight"]

    def __str__(self):
        return self.name
    

class DistanceBand(models.Model):
    name = models.CharField(max_length=200)
    min_km = models.DecimalField(max_digits=10, decimal_places=2)
    max_km = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.min_km} - {self.max_km} km"


class WeightTier(models.Model):
    name = models.CharField(max_length=100)  
    min_weight = models.DecimalField(max_digits=8, decimal_places=2)
    max_weight = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.min_weight}–{self.max_weight} tons)"



class VehiclePricing(models.Model):
    vehicle = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name="vehicle_pricing_rules")
    band = models.ForeignKey(DistanceBand, on_delete=models.CASCADE, related_name="rates", null=True) 
    weight = models.ForeignKey(WeightTier, on_delete=models.CASCADE, related_name="tiers", null=True)
    
    # base price in kms
    base_distance = models.DecimalField(max_digits=10, decimal_places=2, help_text="km included in base price", null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="base price", null=True)
    extra_per_km = models.DecimalField(max_digits=10, decimal_places=2, help_text="kes", null=True)


    class Meta:
        unique_together = (
            "vehicle", "weight", "band", 
        )


    def __str__(self):
        return f"{self.vehicle.name} | {self.weight.name} | {self.band.name}"
    
def generateID(pref):
    random_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{pref}{random_id}"

class Booking(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    booking_id = models.CharField(max_length=20, unique=True, null=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customer")
    vehicle = models.ForeignKey(VehicleType, on_delete=models.SET_NULL, null=True, related_name="booked_vehicle")
    pickup_address = models.CharField(max_length=255)
    pickup_latLng = models.CharField(max_length=70, null=True, verbose_name=_("sender latitude,longitude"))
    dropoff_address = models.CharField(max_length=255)
    origin_office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.SET_NULL, related_name='origin')
    distance =  models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("payment phone"))


    def save(self, *args, **kwargs):
        if not self.booking_id:
            while True:
                new_id = generateID("FL")
                if not Booking.objects.filter(booking_id=new_id).exists():
                    self.booking_id = new_id
                    break

        if not self.origin_office:
            try: 
                lat, lng = map(float, self.pickup_latLng.split(","))
                self.origin_office = self.get_nearest_office(lat, lng)

            except Exception as e:
                print(f"Error parsing sender coordinates: {e}")

        super().save(*args, **kwargs)


    @staticmethod
    def get_nearest_office(lat, lng):
        offices = Office.objects.all()
        package_coords = (float(lat), float(lng))

        nearest = None
        min_distance = float("inf")

        for office in offices:
            office_coords = (float(office.geo_lat), float(office.geo_lng))
            distance = geodesic(package_coords, office_coords).km

            if distance < min_distance:
                min_distance = distance
                nearest = office
        return nearest


    def __str__(self):
        return f"{self.booking_id} ~ by {self.sender.full_name}"



