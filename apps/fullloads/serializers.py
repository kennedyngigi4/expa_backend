from rest_framework import serializers
from apps.fullloads.models import *


class VehicleTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = [
            "id", "name", "description"
        ]


class BookingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id", "sender", "vehicle", "pickup_address", "pickup_latLng", 
            "dropoff_address", "distance", "price", "weight", "created_at", "payment_phone",
            "recipient_name", "recipient_phone"
        ]

        read_only_fields = [
            "id", "sender", "created_at" 
        ]

class BookingReadSerializer(serializers.ModelSerializer):

    vehicle = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "sender", "vehicle", "pickup_address", "pickup_latLng", "dropoff_address", "distance", 
            "price", "weight", "created_at", "payment_phone", "booking_id", "recipient_name", "recipient_phone",
        ]

    def get_vehicle(self, obj):
        return obj.vehicle.name

        

