from decimal import Decimal

from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.cache import cache

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsClient
from apps.fullloads.models import *
from apps.fullloads.serializers import *
from core.utils.services import get_road_distance_km
from core.utils.payments import NobukPayments
# Create your views here.


@method_decorator(cache_page(60 * 60 * 24), name="dispatch")
class VehicleTypesView(generics.ListAPIView):
    serializer_class = VehicleTypesSerializer


    def get_queryset(self):
        cache_key = "vehicle_types_all"
        qs = cache.get(cache_key)

        if qs is None:
            qs = VehicleType.objects.all().order_by("weight")
            cache.set(cache_key, qs, 60 * 60 * 24)
        
        return qs


def find_matching_surge(destination_name, weight_tier):
    destination_name = destination_name.lower()

    surges = Surge.objects.filter(is_active=True)
    matched_surges = []

    for surge in surges:
        keywords = [ k.strip().lower() for k in surge.locations.split(",") ]
        if any(keyword in destination_name for keyword in keywords):
            if surge.weight_tiers.exists():
                surge_tier_ids = surge.weight_tiers.values_list("id", flat=True)
                if weight_tier.id in surge_tier_ids:
                    matched_surges.append(surge)
            else:
                matched_surges.append(surge)
        
    if matched_surges:
        return matched_surges[0]
    
    return None


class CalculateFullloadPrice(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
    
        try:
            weight = Decimal(data.get("weight", "0"))
            vehicle_id = data.get("vehicle")
            origin = data.get("origin_latLng")
            destination = data.get("destination_latLng")
            destination_name = data.get("destination_name", "").lower()

        except Exception as e:
            return Response({"success": False, "message": f"Invalid input: {e}"}, status=400)

        if not all([weight, vehicle_id, origin, destination]):
            return Response({"success": False, "message": "Missing required fields"}, status=400)

        
        try:
            origin_coords = tuple(map(float, origin.split(",")))
            destination_coords = tuple(map(float, destination.split(",")))
        except Exception:
            return Response({"success": False, "message": "Invalid coordinates"}, status=400)

        
        distance_km = get_road_distance_km(origin_coords, destination_coords)
        
        if distance_km is None:
            return Response({"success": False, "message": "Failed to calculate road distance"}, status=400)

        
        band = DistanceBand.objects.filter(min_km__lte=distance_km, max_km__gte=distance_km).first()
        if not band:
            return Response({"success": False, "message": "No pricing band for this distance"}, status=404)

        
        weight_tier = WeightTier.objects.filter(min_weight__lte=weight, max_weight__gte=weight).first()
        if not weight_tier:
            return Response({"success": False, "message": "No weight tier for this weight"}, status=404)

        
        try:
            vehicle = VehicleType.objects.get(id=vehicle_id)
        except VehicleType.DoesNotExist:
            return Response({"success": False, "message": "Invalid vehicle"}, status=404)

        
        rate = VehiclePricing.objects.filter(
            vehicle=vehicle,
            band=band,
            weight=weight_tier
        ).first()

        if not rate:
            return Response({"success": False, "message": "No rate configured for this request"}, status=404)

        if distance_km <= rate.base_distance:
            total = Decimal(rate.base_price)
        else:
            extra_km = Decimal(str(distance_km)) - rate.base_distance
            total = rate.base_price + (extra_km * rate.extra_per_km)

        print(total)


        surge_applied = None
        surge_amount = Decimal("0")
        matched_surge = find_matching_surge(destination_name, weight_tier)
        

        if matched_surge:
            if matched_surge.surge_increase_percent:
                surge_amount = (matched_surge.surge_increase_percent / Decimal("100")) * total

                total += surge_amount
                surge_applied = {
                    "type": "increase",
                    "percent": matched_surge.surge_increase_percent
                }

            elif matched_surge.decrease_percent:
                surge_amount = (matched_surge.decrease_percent / 100) * total
                total -= surge_amount
                surge_applied = {
                    "type": "decrease",
                    "percent": matched_surge.decrease_percent
                }
        print(f"Total: {total}")

        return Response({
            "success": True,
            "distance_km": round(distance_km, 2),
            "vehicle": vehicle.name,
            "weight_tier": weight_tier.name,
            "band": band.name,
            "price": round(total, 2),
        })
        



class FullloadCreationView(APIView):
    permission_classes = [ IsAuthenticated ]

    def post(self, request, *args, **kwargs):
        serializer = BookingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mpesa_phone = request.data["payment_phone"]
        order = serializer.save(sender=self.request.user)

        
        
        if order:
            NobukPayments(mpesa_phone, self.request.user.full_name, order.booking_id, str(round(order.price)), "web").STKPush()

        return Response({
            "success": True,
            "message": "Booked successfully.",
        }, status=status.HTTP_201_CREATED)


