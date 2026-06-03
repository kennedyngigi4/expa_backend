import logging
import datetime
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from core.utils.services import *
from decimal import Decimal
from django.utils import timezone

from apps.deliveries.models import Package
from apps.payments.models import Invoice
from apps.messaging.views import intracity_drivers_notification
from apps.messaging.utils import send_notification
from django.db import transaction
from core.utils.payments import NobukPayments, CashPayments
from apps.messaging.utils import send_message
from core.utils.emails import send_order_creation_email, send_order_creation_email_admin

logger = logging.getLogger(__name__)

# 2 minutes between rounds
ROUND_DELAY = 120  



@shared_task(name="apps.deliveries.tasks.process_package_invoice")
def process_package_invoice(package_id):
    try:
        package = Package.objects.get(id=package_id)
        user = package.created_by

        if hasattr(package, "invoice"):
            return "Invoice already exists"
        
        status = "unpaid" if user.account_type == "personal" else "pending"
        invoice = Invoice.objects.create(
            user=user, package=package, amount=Decimal(round(package.fees, 3)), status=status
        )
        invoice_id = invoice.id
        amount = str(int(invoice.amount))

        

        if user.account_type == "personal":
            if package.payment_method == "mpesa":
                payments = NobukPayments(
                    package.payment_phone,
                    package.sender_name,
                    str(invoice_id),
                    amount,
                    "web"
                ).STKPush()
                

                # send sms
                send_message(package.recipient_phone, f"Dear {package.recipient_name}, a package (Ref: {package.package_id}) has been sent to you via ExPa Logistics by {package.sender_name}. We will update you once it is out for delivery.")
                send_message(package.sender_phone, f"Dear {package.sender_name}, your package (Ref: {package.package_id}) has been successfully submitted to ExPa for delivery. We will notify you once it is dispatched. Thank you for choosing ExPa Logistics.")
                
                # In-app notifications
                send_notification(user=user, title=f"Order {package.package_id}", message="You order was submitted successfully.")

            elif package.payment_method == "card":
                print("Payment via card – task only.")

            elif package.payment_method == "cash":
                CashPayments(
                    amount,
                    package.sender_user,
                    str(invoice_id),
                    package.payment_method,
                ).register_transaction()

        # Emails
        send_order_creation_email(user, package)
        send_order_creation_email_admin(user, package)

        return "Invoice and notifications processed"
    except Package.DoesNotExist:
        return "Package not found"


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def send_intracity_notifications(self, package_id, round_number=1, total_rounds=2):
    try:
        package = Package.objects.select_related("origin_office").get(id=package_id)
    except Package.DoesNotExist:
        logger.warning(f"⚠️ Package {package_id} not found when sending notifications.")
        return


    # Only notify paid orders
    if not package.is_paid:
        logger.info(
            f"💰 Package {package.package_id} is not paid "
            f"(status={package.payment_status}). Skipping notifications."
        )
        return

    
    if package.status in ["assigned", "in_transit", "delivered"]:
        logger.info(f"✅ Package {package.package_id} already accepted, skipping notification.")
        return

    
    if not package.sender_latLng:
        logger.warning(f"⚠️ Missing sender location for {package.package_id}")
        return

    try:
        lat, lng = package.sender_latLng.split(",")
        pickup_coords = (float(lat.strip()), float(lng.strip()))
    except ValueError:
        logger.error(f"❌ Invalid sender lat/lng for {package.package_id}")
        return

    
    drivers = get_nearby_drivers(pickup_coords, radius_km=10)
    if drivers:
        intracity_drivers_notification(
            drivers=drivers,
            title=f"🚚 New Intracity Order {package.package_id}",
            body=f"Pickup at {package.sender_address}",
            data={"type": "new_order", "order_id": str(package.id)},
        )
        logger.info(f"📣 Round {round_number}: notified {len(drivers)} drivers for {package.package_id}")
    else:
        logger.warning(f"⚠️ Round {round_number}: no drivers nearby for {package.package_id}")

    
    if round_number < total_rounds:
        transaction.on_commit(
            lambda: send_intracity_notifications.apply_async(
                args=[package.id, round_number + 1, total_rounds], countdown=ROUND_DELAY
            )
        )
        logger.info(
            f"⏱ Scheduled next notification round ({round_number + 1}/{total_rounds}) "
            f"for {package.package_id} in {ROUND_DELAY}s"
        )
    else:
        transaction.on_commit(
            lambda: check_order_acceptance.apply_async(args=[package.id], countdown=ROUND_DELAY)
        )
        logger.info(f"🔚 All rounds sent for {package.package_id}. Escalation check scheduled.")




@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def check_order_acceptance(self, package_id):
    try:
        package = Package.objects.select_related("origin_office").get(id=package_id)
    except Package.DoesNotExist:
        logger.warning(f"⚠️ Package {package_id} not found for acceptance check.")
        return

    package.refresh_from_db()
    logger.warning(f"🔍 Final check for package {package.package_id}: status={package.status}")

    if package.status not in ["assigned", "in_transit", "delivered"]:
        logger.error(f"🚨 Package {package.package_id} still not accepted. Escalating to manager.")
        _escalate_to_manager(package)
    else:
        logger.info(f"✅ Package {package.package_id} accepted, no escalation needed.")


def _escalate_to_manager(package):
    logger.warning(f"🚨 Escalation triggered for package {package.package_id}")

    if not package.origin_office:
        logger.warning(f"⚠️ No origin office for {package.package_id}, cannot escalate.")
        return

    managers = User.objects.filter(role__iexact="manager", office=package.origin_office)
    if not managers.exists():
        logger.warning(f"⚠️ No managers found for office {package.origin_office}.")
        return

    for manager in managers:
        try:
            send_notification(
                user=manager,
                title="⚠️ No Driver Accepted Order",
                message=f"No driver accepted delivery of {package.package_id}. Please assign manually.",
                package=package
            )
            logger.info(f"📤 Escalation notification sent to manager {manager.id}")
        except Exception as e:
            logger.exception(f"❌ Failed to send escalation notification to manager {manager.id}: {e}")

    logger.warning(f"🚨 Escalated to {managers.count()} manager(s) for package {package.package_id}")

