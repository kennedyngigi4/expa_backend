import datetime
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache

from apps.accounts.models import *
from apps.deliveries.models import *
from apps.deliveries.tasks import send_intracity_notifications
from apps.messaging.utils import send_notification
from apps.payments.models import Invoice
from apps.messaging.models import Notification
from apps.messaging.views import *
from decimal import Decimal

from core.utils.emails import send_order_creation_email, send_order_creation_email_admin
from core.utils.payments import NobukPayments
from apps.messaging.utils import send_message


@receiver(post_save, sender=Package)
def send_delivery_notifications_to_drivers(sender, instance, created, **kwargs):
    if not created:
        return 

    # for intra_city
    if instance.delivery_type == "intra_city":
        _schedule_driver_notification(instance)

    elif instance.delivery_type == "inter_county" and instance.requires_pickup:
        _schedule_driver_notification(instance)


def _schedule_driver_notification(instance):
    if instance.pickup_date:
        eta = timezone.make_aware(instance.pickup_date) if timezone.is_naive(instance.pickup_date) else instance.pickup_date

        if eta > timezone.now():
            send_intracity_notifications.apply_async(
                args=(instance.id,), 
                eta=eta
            )
        else:
            send_intracity_notifications.delay(instance.id)

    else:
        send_intracity_notifications.delay(instance.id)

                


@receiver(post_save, sender=Package)
def create_invoice(sender, instance, created, **kwargs):
    if created:
        from apps.deliveries.tasks import process_package_invoice
        process_package_invoice.delay(instance.id)
    

    
@receiver(post_save, sender=Package)
def notify_on_partner_upload(sender, instance, created, **kwargs):
    user = instance.created_by

    if not created or user.role != "partner_shop":
        return
    
    office = instance.origin_office
    package = instance

    # Notify office personel
    managers = User.objects.filter(role="manager", office=office)
    for manager in managers:
        Notification.objects.create(
            user=manager,
            title=f"New Partner Package - {package.package_id}",
            message=f"{user.full_name} uploaded a package at {office.name}.",
            package=package
        )

    # Notify the creator
    Notification.objects.create(
        user=user,
        title=f"{package.package_id} Upload Confirmed",
        message=f"Your package, {package.package_id} to {office.name} was uploaded successfully.",
        package=package
    )



@receiver(post_save, sender=Shipment)
def notify_assigned_courier(sender, instance, created, **kwargs):
    if created and instance.courier:
        Notification.objects.create(
            user=instance.courier,
            title=f"New Shipment Assigned - {instance.shipment_id}",
            message=f"You have been assigned a new shipment: {instance.shipment_id}. Shipment type: {instance.shipment_type} at {instance.origin_office}.",
            shipment=instance,
            notification_type="assignment",
        )


        # update all packages linked to the shipment
        package_ids = ShipmentPackage.objects.filter(
            shipment=instance
        ).values_list("package_id", flat=True)

        if package_ids:
            Package.objects.filter(id__in=package_ids).update(
                current_handler=instance.courier
            )


@receiver([post_save, post_delete], sender=Package)
def clear_user_packages_cache(sender, instance, **kwargs):
    if instance.created_by_id:
        cache.delete(f"user_packages_{instance.created_by_id}")






