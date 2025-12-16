from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.accounts.models import *
from apps.international.models import *
# Create your views here.



class InternationalCalculator(APIView):

    def post(self, request):
        try:
            data = request.data
            weight = Decimal(data.get("wight", 0))
            city = data.get("city")

            

        except Exception as e: 
            return Response({"success": False, "message": str(e)}, status=500)

    


