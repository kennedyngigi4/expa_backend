import random
import string
import uuid
from django.db import models
from apps.accounts.models import User
# Create your models here.

class Country(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name
    

class City(models.Model):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def __str__(self):
        return f"{self.name}, {self.country.name}"



class InternationalPolicy(models.Model):

    city = models.ForeignKey(City, on_delete=models.CASCADE)
    min_weight = models.DecimalField(max_digits=12, decimal_places=2)
    max_weight = models.DecimalField(max_digits=12, decimal_places=2)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_flat_price = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.city.name} - {self.max_weight} - {self.base_price}"
    


def generateID(pref):
    random_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{pref}{random_id}"


class InternationalOrders(models.Model):

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4, unique=True)
    order_id = models.CharField(max_length=100, unique=True)
    
    name = models.CharField(max_length=255, null=True)
    is_fragile = models.BooleanField(default=False)
    weight = models.DecimalField(max_digits=10, decimal_places=2)

    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=30)
    recipient_email = models.EmailField()
    description = models.TextField(null=True, blank=True)

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender")
    sender_name = models.CharField(max_length=15, null=True)
    sender_phone = models.CharField(max_length=15)

    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, related_name="city")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mpesaphone = models.CharField(max_length=30, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)


    def save(self, *args, **kwargs):
        if not self.order_id:
            while True:
                new_id = generateID("INT")
                if not InternationalOrders.objects.filter(order_id=new_id).exists():
                    self.order_id = new_id
                    break

        return super().save(*args, **kwargs)


    def __str__(self):
        return f"Sent by {self.sender.full_name} to {self.recipient_name} in {self.recipient_city.name}"


