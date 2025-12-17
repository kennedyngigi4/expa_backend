from rest_framework import serializers
from apps.international.models import *


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [ "id", "name" ]      



class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = [ "id", "name", "country" ]   




class WriteOrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = InternationalOrders
        fields = [
            "name", "is_fragile", "city", "weight", "recipient_name", "recipient_phone", "recipient_email", 
            "description", "mpesaphone", "sender_name", "sender_phone", "price"
        ]


