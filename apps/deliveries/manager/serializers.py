from rest_framework import serializers
from apps.deliveries.models import *

class PackageItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageItem
        fields = [
            "destination", "destination_latLng", "weight", "description", "price", "no_items", "recipient_name", "recipient_phone"
        ]


class ManagerPackageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            'name', 'is_fragile', 'sender_name', 'sender_phone', 'sender_address', 'recipient_name', 'recipient_phone', 
            'recipient_address', 'requires_pickup', 'requires_last_mile', 'payment_phone', 'payment_method', 'size_category', 
            'fees', 'sender_latLng', 'recipient_latLng', 'delivery_type', 'weight'
        ]


class ManagerPackageReadSerializer(serializers.ModelSerializer):
    package_items = PackageItemsSerializer(many=True, required=False)
    urgency_name = serializers.SerializerMethodField()
    package_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Package
        fields = [
            "slug","name", "package_type", "package_type_name", "size_category", "delivery_type", "is_fragile", "urgency", "urgency_name", "weight", "pickup_date", 
            "description", "sender_name", "sender_phone", "sender_address", "sender_latLng", "is_paid", "recipient_name",
            "recipient_phone", "recipient_address", "recipient_latLng", "package_id", "status", "requires_last_mile", 
            "requires_pickup", "fees", "vehicle_type", "package_items", "requires_packaging"
        ]
        
    def get_urgency_name(self, obj):
        if obj.urgency:
            return obj.urgency.name
        return None


    def get_package_type_name(self, obj):
        return getattr(obj.package_type, "name", None)


