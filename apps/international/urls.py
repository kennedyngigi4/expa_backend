from django.urls import path
from apps.international.views import *



urlpatterns = [
    path( "calculator/", InternationalCalculator.as_view(), name="calculator", ),
]


