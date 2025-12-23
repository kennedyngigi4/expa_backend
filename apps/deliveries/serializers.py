from django.forms import ValidationError
from rest_framework import serializers

from apps.accounts.models import *
from apps.deliveries.models import VehicleType, VehiclePricing, PackageType, Package, Shipment, SizeCategory, InterCountyRoute, ShipmentPackage, ShipmentTracking, HandOver, UrgencyLevel, ShipmentStage, ProofOfDelivery
from apps.messaging.models import Notification




class SizeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeCategory
        fields = [
            "id","name", "max_length", "max_width", "max_height", "description", "base_price"
        ]


class PackageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageType
        fields = [
            'id', 'name', 'price'
        ]


class UrgencyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = UrgencyLevel
        fields = [
            "id", "name", "description", "surcharge_type", "surcharge_amount"
        ]


class VehicleTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = [
            "id", "name", "description"
        ]


class InterCountyRouteSerializer(serializers.ModelSerializer):

    origins = serializers.SerializerMethodField()
    destinations = serializers.SerializerMethodField()
    size_category = serializers.SerializerMethodField()

    class Meta:
        model = InterCountyRoute
        fields = [
            "origins", "destinations", "size_category", "base_weight_limit", "base_price",
        ]

    def get_size_category(self, obj):
        return obj.size_category.name

    def get_origins(self, obj):
        origins = ", ".join([office.name for office in obj.origins.all()])
        return origins
    
    def get_destinations(self, obj):
        destinations = ", ".join([office.name for office in obj.destinations.all()])
        return destinations



class ProofOfDeliverySerializer(serializers.ModelSerializer):
    

    class Meta:
        model = ProofOfDelivery
        fields = [
            "id", "shipment", "package", "identity_number", "status", "name", "created_at", "note"
        ]
        
    


class PackageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            "slug","name", "package_type", "size_category", "delivery_type", "is_fragile", "urgency",
            "length", "width", "height", "weight", "pickup_date", "description", "sender_name", "sender_phone", "sender_address", 
            "sender_latLng", "is_paid", "recipient_name", "recipient_phone", "recipient_address", "recipient_latLng", "requires_packaging",
            "package_id", "status", "requires_last_mile", "requires_pickup", "fees", "payment_phone", "pickup_now", "payment_method"
        ]
        read_only_fields = [
            "id", "package_id", "current_handler", "delivery_stage_count", "current_stage", "cardholder_name", "card_number", "card_expiry", "card_cvc"
        ]




class PackageSerializer(serializers.ModelSerializer):
    size_category_name = serializers.SerializerMethodField()
    urgency_name = serializers.SerializerMethodField()
    package_type_name = serializers.SerializerMethodField()
    rider_location = serializers.SerializerMethodField()
    package_proofs = ProofOfDeliverySerializer(many=True, read_only=True)
    manager_office_id = serializers.SerializerMethodField()

    class Meta:
        model = Package
        fields = [
            "id","slug","name", "package_type", "package_type_name", "size_category", "size_category_name", "delivery_type", "is_fragile", "urgency", "urgency_name",
            "length", "width", "height", "weight", "pickup_date", "description", "sender_name", "sender_phone", "sender_address", 
            "sender_latLng", "is_paid", "recipient_name", "recipient_phone", "recipient_address", "recipient_latLng", "requires_packaging",
            "package_id", "status", "created_by_role", "created_at", "fees", "rider_location", "payment_method", 
            "package_proofs", "current_office", "manager_office_id", "qrcode_svg"
        ]
        read_only_fields = [
            "id", "package_id", "current_handler", "delivery_stage_count", "current_stage"
        ]


    def get_size_category_name(self, obj):
        if obj.size_category:
            return obj.size_category.name
        return None
    
    def get_urgency_name(self, obj):
        if obj.urgency:
            return obj.urgency.name
        return None
    

    def get_package_type_name(self, obj):
        return getattr(obj.package_type, "name", None)


    def get_rider_location(self, obj):
        shipment = obj.shipments.order_by("-assigned_at").first()

        if not shipment or shipment.status not in ["in_transit", "assigned", "with_courier"]:
            return None
        
        courier = shipment.courier
        if not courier:
            return None

        data = {
            "id": courier.id,
            "name": courier.full_name,
            "phone": courier.phone,
            "lat": None,
            "lng": None,
            "updated_at": None
        }

        try: 
            location = courier.location
            data.update({
                "lat": location.latitude,
                "lng": location.longitude,
                "updated": location.updated_at,

            })

        except DriverLocation.DoesNotExist:
            return None
        
        return data

    def get_manager_office_id(self, obj):
        user = self.context["request"].user
        if user.role == "manager" and hasattr(user, "office"):
            return str(user.office.id)
        return None


class PackageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [ 
            "id", "slug","name", "package_id", "status", "sender_address", "recipient_address", "recipient_name", "is_paid"
        ]


class ShipmentPackageSerializer(serializers.ModelSerializer):
    package = PackageSerializer()
    class Meta:
        model = ShipmentPackage
        fields = [
            "shipment", "package", "status", "delivered", "notes", "confirmed_by", "confirmed_at", "receiver_signature"
        ]



class ShipmentSerializer(serializers.ModelSerializer):
    packages = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True
    )

    class Meta:
        model = Shipment
        fields = [
            "shipment_id","shipment_type", "packages", "origin_office", "destination_office", "status", "courier", "requires_handover", 
            "pickup_location", "pickup_latLng", "destination_location", "destination_latLng",
        ]


    def create(self, validated_data):
        request = self.context["request"]
        
        # Use manager from validated_data if provided (by view), otherwise default
        manager = validated_data.pop("manager", getattr(request.user, "id", None))
        if manager is None:
            raise ValidationError("Manager must be set either in view or request context.")

        packages_data = validated_data.pop("packages", [])

        # Set origin_office if missing
        if not validated_data.get("origin_office") and hasattr(request.user, "office"):
            validated_data["origin_office"] = request.user.office

        shipment = Shipment.objects.create(manager=manager, **validated_data)

        # Link packages
        for package_id in packages_data:
            try:
                package = Package.objects.get(id=package_id)
                ShipmentPackage.objects.create(shipment=shipment, package=package)
                package.status = "assigned"
                package.save()
                self.send_package_notification(package)
            except Package.DoesNotExist:
                continue

        # Initial ShipmentStage
        ShipmentStage.objects.create(
            shipment=shipment,
            stage_number=1,
            driver=shipment.courier,
            status="created",
            handover_required=shipment.requires_handover
        )

        return shipment
    

    def send_package_notification(self, package):
        Notification.objects.create(
            user=package.sender_user,  # recipient
            title="Your package has been assigned to a shipment",
            message=f"Package {package.package_id} is being prepared for delivery.",
            notification_type="shipment_update"
        )



class ShipmentStageSerializers(serializers.ModelSerializer):

    driver = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentStage
        fields = [
            "shipment", "stage_number", "driver", "driver_phone", "from_office", "to_office", "status", "created_at"
        ]

    def get_driver(self, obj):
        return obj.driver.full_name
    
    def get_driver_phone(self, obj):
        return obj.driver.phone



class ShipmentReadSerializer(serializers.ModelSerializer):
    packages = serializers.SerializerMethodField()
    stages = ShipmentStageSerializers(many=True)
    destinationoffice = serializers.SerializerMethodField()
    originoffice = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    

    class Meta:
        model = Shipment
        fields = [
            "id", "shipment_id","shipment_type", "packages", "origin_office", "pickup_location", "originoffice", "destination_office", 
            "destinationoffice", "destination_location", "status", "courier", "stages", "current_stage", "summary", "qrcode_svg", "assigned_at"
        ]


    def get_summary(self, obj):
        packages = obj.shipmentpackage_set.all()
        if obj.shipment_type == "pickup":
            sources = set(p.package.sender_address for p in packages)
            if obj.origin_office:
                return f"Pickup from {len(sources)} client(s) to {obj.origin_office.name}"
            else:
                return f"Pickup from {len(sources)} client(s)"
            
        elif obj.shipment_type == "delivery":
            destinations = set(p.package.recipient_address for p in packages)
            return f"Deliver from {obj.origin_office.name} to {len(destinations)} client(s)"
        
        elif obj.shipment_type == "transfer":
            return f"Transfer from {obj.origin_office.name} to {obj.destination_office.name}"
        
        elif obj.shipment_type == "complete":
            return f"{len(packages)} direct delivery(s)"
        return "Shipment"


    def get_packages(self, obj):
        shipment_packages = ShipmentPackage.objects.filter(shipment=obj)
        return ShipmentPackageSerializer(shipment_packages, many=True, context=self.context).data


    def get_originoffice(self, obj):
        if obj.origin_office:
            return obj.origin_office.name
        return None
    
    def get_destinationoffice(self, obj):
        if obj.destination_office:
            return obj.destination_office.name
        return None 
    
    
    def get_current_stage(self, obj):
        return obj.current_stage
    


class ShipmentUpdateSerializer(serializers.ModelSerializer):
    driver_accepted = serializers.BooleanField()

    class Meta:
        model = Shipment
        fields = ["driver_accepted"]

    def update(self, instance, validated_data):
        driver_accepted = validated_data.get("driver_accepted")

        if driver_accepted:
            instance.status = "in_transit"
            instance.current_stage = 1
            instance.save(update_fields=["driver_accepted", "status", "current_stage"])

            # notify manager and package owners
            self.send_notifications(instance)
        return instance

    def send_notifications(self, shipment):
        # Notify manager
        if shipment.manager:
            Notification.objects.create(
                user=shipment.manager,
                title="Shipment accepted",
                message=f"Driver has accepted shipment {shipment.shipment_id}",
                shipment=shipment,
                notification_type="shipment_update"
            )

        # Notify all package owners
        for package in shipment.packages.all():
            Notification.objects.create(
                user=package.created_by,
                title="Package in Transit",
                message=f"Your package {package.package_id} is now in transit.",
                package=package,
                notification_type="shipment_update"
            )





