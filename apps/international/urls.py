from django.urls import path
from apps.international.views import *



urlpatterns = [
    path( "countries/", CountriesView.as_view(), name="countries", ),
    path( "cities/<str:pk>/", CitiesView.as_view(), name="cities", ),
    path( "pricing/", InternationalPricingView.as_view(), name="pricing", ),
    path( "add_order/", CreateOrderView.as_view(), name="add_order"),
]


