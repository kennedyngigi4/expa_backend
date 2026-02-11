from django.shortcuts import render, get_object_or_404

from rest_framework import generics, status
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db.models import Q

from apps.accounts.models import *
from apps.accounts.permissions import *
from apps.deliveries.models import *
from apps.deliveries.serializers import *
from apps.deliveries.manager.serializers import *


class ManagerDashboardStatsView(APIView):
    permission_classes = [ IsManager, IsAuthenticated]

    def get(self, request):
        user = self.request.user

        if not hasattr(user, 'office'):
            return Response({ "success": False, "message": "Manager is not linked to any office."}, status=400)

        office = user.office

        packages = Package.objects.filter(origin_office=office)
        shipments = Shipment.objects.all()

        orders = packages.count()
        unassigned_orders = packages.filter(shipments=None).count()
        shipments_out = shipments.filter(origin_office=office).count()
        shipments_in = shipments.filter(destination_office=office).count()
        outgoing_shipments = Shipment.objects.filter(manager=user, origin_office=office).order_by("-assigned_at")
        recent_shipments = ShipmentReadSerializer(outgoing_shipments, many=True, context={"request": request}).data

        return Response({
            "orders": orders,
            "unassigned_orders": unassigned_orders,
            "shipments_out": shipments_out,
            "shipments_in": shipments_in,
            "recent_shipments": recent_shipments,
        })






class ManagerOriginPackagesView(ListAPIView):
    serializer_class = PackageSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        user = self.request.user
        category = self.request.query_params.get("category")
        delivery_type = self.request.query_params.get("delivery_type")

        office = getattr(user, "office", None)
        if not office:
            return Package.objects.none()

        queryset = Package.objects.all().order_by("-created_at")

        
        if delivery_type in ["intra_city", "inter_county", "international"]:
            queryset = queryset.filter(delivery_type=delivery_type)

        
        if category == "pending":
            queryset = queryset.filter(
                origin_office=office,
                status="pending",
                shipments__isnull=True
            )

        elif category == "assigned":
            queryset = queryset.filter(
                origin_office=office,
                status="assigned",
                shipments__isnull=False
            )

        elif category == "in_transit":
            queryset = queryset.filter(
                origin_office=office,
                shipments__status="in_transit"
            )

        elif category == "delivered":
            queryset = queryset.filter(
                origin_office=office,
                status="delivered"
            )

        elif category == "received":
            queryset = queryset.filter(
                destination_office=office,
                status="received"
            )

        elif category in ["all", None]:
            queryset = queryset.filter(
                origin_office=office
            )

        return queryset.distinct()





class ManagerIncomingPackagesView(ListAPIView):
    serializer_class = PackageSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        user = self.request.user
        category = self.request.query_params.get("category")
        delivery_type = self.request.query_params.get("delivery_type")

        office = getattr(user, "office", None)
        if not office:
            return Package.objects.none()

        queryset = Package.objects.all().order_by("-created_at")

        
        if delivery_type in ["intra_city", "inter_county", "international"]:
            queryset = queryset.filter(delivery_type=delivery_type)

        
        if category == "pending":
            queryset = queryset.filter(
                destination_office=office,
                status="pending",
                shipments__isnull=True
            )

        elif category == "assigned":
            queryset = queryset.filter(
                destination_office=office,
                status="assigned",
                shipments__isnull=False
            )

        elif category == "in_transit":
            queryset = queryset.filter(
                destination_office=office,
                shipments__status="in_transit"
            )
        
        elif category == "in_office":
            queryset = queryset.filter(
                destination_office=office,
                status="in_office"
            )

        elif category == "delivered":
            queryset = queryset.filter(
                destination_office=office,
                status="delivered"
            )

        

        elif category in ["all", None]:
            queryset = queryset.filter(
                destination_office=office
            )

        return queryset.distinct()



class ManagerPackageDetailsView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ManagerPackageReadSerializer
    queryset = Package.objects.all()
    permission_classes = [IsAuthenticated, IsManager]



class ManagerCreateShipmentView(generics.ListCreateAPIView):
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated, IsManager]
    queryset = Shipment.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        office = getattr(user, "office", None)
        if not office:
            raise ValidationError({"office": "Manager is not linked to any office."})

        shipment_type = serializer.validated_data.get("shipment_type")

        # ✅ Only set the manager and office here
        if shipment_type == "pickup":
            serializer.save(
                manager=user,
                destination_office=office, 
            )
        else:
            serializer.save(manager=user)

    def post(self, request, *args, **kwargs):
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as ve:
            print("VALIDATION ERRORS:", ve.detail)
            return Response({"success": False, "errors": ve.detail}, status=400)

        except Exception as e:
            print("ERROR CREATING SHIPMENT:", str(e))
            return Response({"success": False, "message": str(e)}, status=500)




class ManagerListShipmentView(generics.ListCreateAPIView):
    serializer_class = ShipmentReadSerializer
    permission_classes = [IsAuthenticated, IsManager]
    queryset = Shipment.objects.all()

    def get_queryset(self):
        user = self.request.user
        category = self.request.query_params.get("category")

        if not user.office:
            return Shipment.objects.none()
        
        queryset = Shipment.objects.filter(manager=user, origin_office=user.office).order_by("-assigned_at")

        if category == "assigned":
            queryset = queryset.filter(status="created")
        elif category == "in_transit":
            queryset = queryset.filter(status="in_transit")
        elif category == "received":
            queryset = queryset.filter(confirm_received=True)
        elif category == "delivered":
            queryset = queryset.filter(status="delivered")
        elif category == "returned":
            queryset = queryset.filter(status="returned")
        elif category == "cancelled":
            queryset = queryset.filter(status="cancelled")

        elif category == "all":
            queryset = queryset

        return queryset





class ManagerIncomingShipmentsView(generics.ListAPIView):
    serializer_class = ShipmentReadSerializer
    permission_classes = [IsAuthenticated, IsManager]
    queryset = Shipment.objects.all()


    def get_queryset(self):
        user = self.request.user
        category = self.request.query_params.get("category")

        if not user.office:
            return Shipment.objects.none()
        
        queryset = self.queryset.filter(destination_office=user.office)
        if category == "assigned":
            queryset = queryset.filter(status="created")
        elif category == "in_transit":
            queryset = queryset.filter(status="in_transit")
        elif category == "delivered":
            queryset = queryset.filter(status="delivered")
        elif category == "returned":
            queryset = queryset.filter(status="returned")
        elif category == "cancelled":
            queryset = queryset.filter(status="cancelled")
        elif category == "all":
            queryset = queryset

        print(queryset)
        
        return queryset




class ManagerShipmentDetailsView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class = ShipmentReadSerializer
    queryset = Shipment.objects.all()
    


class ManagerConfirmShipmentReceivedView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    
    def post(self, request, pk):
        try:
            shipment = Shipment.objects.get(id=pk)

            # Ensure its by the receiving manager
            if hasattr(self.request.user, "office") and shipment.destination_office != request.user.office:
                return Response(
                    {"detail": "You are not authorized to confirm this shipment."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            #1. Update shipment
            shipment.confirm_received = True
            shipment.status = PackageStatus.RECEIVED
            shipment.save()

            # 2. Update ShipmentPackage
            shipment_packages = ShipmentPackage.objects.filter(shipment=shipment)
            shipment_packages.update(status=PackageStatus.RECEIVED)


            # 3. Update all Packages linked via ShipmentPackages
            Package.objects.filter(
                id__in=shipment_packages.values_list("package", flat=True)
            ).update(status=PackageStatus.RECEIVED)

            return Response(
                {"detail": "Shipment and related packages marked as received."},
                status=status.HTTP_200_OK
            )
        
        except Shipment.DoesNotExist:
            return Response(
                {"detail": "Shipment not found."},
                status=status.HTTP_404_NOT_FOUND
            )
