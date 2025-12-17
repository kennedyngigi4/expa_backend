from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import *
from apps.international.models import *
from apps.international.serializers import *
from core.utils.payments import NobukPayments
# Create your views here.


class CountriesView(generics.ListAPIView):
    serializer_class = CountrySerializer
    queryset = Country.objects.all().order_by("name")


class CitiesView(generics.ListAPIView):
    serializer_class = CitySerializer
    
    def get_queryset(self):
        country_id = self.kwargs["pk"]
        return City.objects.filter(country_id=country_id).order_by("name")


class InternationalPricingView(APIView):

    def post(self, request):
        try:
            data = request.data
            city = data.get("city")
            weight = Decimal(data.get("weight", 0))
            policy = InternationalPolicy.objects.filter(
                city_id=int(city),
                min_weight__lte=weight,
                max_weight__gte=weight
            ).first()

            if not policy:
                return Response({ "success": False, "message": "There is no weight policy for that city."  })
            

            base_fee = Decimal("0.00")
            if policy.is_flat_price:
                base_fee = policy.base_price

            else:
                base_fee = weight * policy.base_price
            
            
            return Response({
                "success": True,
                "total_fee": base_fee,
            })


        except Exception as e: 
            return Response({"success": False, "message": str(e)}, status=500)

    

class CreateOrderView(generics.CreateAPIView):
    serializer_class = WriteOrderSerializer
    queryset = InternationalOrders.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        serializer = WriteOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(sender=self.request.user, created_by=self.request.user)
        

        NobukPayments(order.mpesaphone, order.sender_name, str(order.order_id), str(int(order.price)), "web").STKPush()

        return Response({ "success": True, "message": "Upload successful."})
