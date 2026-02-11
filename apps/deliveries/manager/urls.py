from django.urls import path
from apps.deliveries.manager.views import *




urlpatterns = [
    path( "dashboard/", ManagerDashboardStatsView.as_view(), name='dashboard', ),
    path( "origin_packages/", ManagerOriginPackagesView.as_view(), name="origin_packages", ),
    path( "incoming_packages/", ManagerIncomingPackagesView.as_view(), name="incoming_packages", ),
    path( "package_details/<str:pk>/", ManagerPackageDetailsView.as_view(), name="package_details", ),
    path( "create_shipment/", ManagerCreateShipmentView.as_view(), name="create_shipment", ),
    path( "shipments/", ManagerListShipmentView.as_view(), name="shipments", ),
    path( "shipment_details/<str:pk>/", ManagerShipmentDetailsView.as_view(), name="shipment_details", ),
    path( "incoming_shipments/", ManagerIncomingShipmentsView.as_view(), name="incoming_shipments", ),
    path( "shipments/<str:pk>/confirm-received/", ManagerConfirmShipmentReceivedView.as_view(), name="confirm-received",),
]



