from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.accounts.models import *
from apps.international.models import *
# Create your views here.



class InternationalCalculator(APIView):

    def post(self, request):
        pass

    


