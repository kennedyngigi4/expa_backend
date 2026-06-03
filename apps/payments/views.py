import json
from django.shortcuts import render
from django.template.loader import select_template, render_to_string
from django.http import HttpResponse

from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import red, green, white, black
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator



from apps.accounts.permissions import IsAdmin
from apps.deliveries.signals import _schedule_driver_notification
from apps.payments.models import *
from apps.payments.serializers import *
from apps.payments.services import consolidated_invoices
# Create your views here.


class InvoicesView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all().order_by("-issued_at")
    permission_classes = [ IsAuthenticated ]


    def get_queryset(self):
        user = self.request.user

        queryset = Invoice.objects.filter(user=user).order_by("-issued_at")

        month = self.request.query_params.get("month")
        status = self.request.query_params.get("status")
        
        # filter by month if provided
        if month:
            try:
                queryset = queryset.filter(issued_at__month=int(month))
            except (ValueError, TypeError):
                pass

        if status:
            queryset = queryset.filter(status__iexact="status")

        return queryset




   


def draw_status(canvas, doc, status):
    width, height = A4

    # Choose colors based on status
    if status and status.lower() == "paid":
        bg_color = colors.green
        text_color = colors.white
        label = "PAID"
    else:
        bg_color = colors.red
        text_color = colors.white
        label = "UNPAID"

    canvas.saveState()

    # Move near top right corner
    canvas.translate(width - 110, height - -20)

    # Rotate ~330 degrees
    canvas.rotate(320)

    # Draw rectangle (strip)
    canvas.setFillColor(bg_color)
    canvas.rect(0, 0, 200, 30, fill=1, stroke=0)

    # Add text
    canvas.setFillColor(text_color)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawCentredString(90, 8, label)

    canvas.restoreState()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_invoice_pdf(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    elements = []

    # Title
    expa = Paragraph("Express Parcel", styles["Heading2"])
    expa_contacts = Paragraph("0722 620 988 / 0734 620 988")
    expa_payments = Paragraph("Invoice details")
    elements.extend([expa, expa_contacts, expa_payments, Spacer(1, 30)])

    # "We have to" section
    if getattr(request.user, "corporate_office", None):
        recipient_company = Paragraph(f"{request.user.corporate_office}", styles["Heading4"])
        elements.append(recipient_company)

    recipient_name = Paragraph(f"{request.user.full_name}")
    recipient_email = Paragraph(f"{request.user.email}")
    elements.extend([recipient_name, recipient_email, Spacer(1, 29)])

    # Invoice details
    invoice_id_para = Paragraph(f"#{invoice.invoice_id}", styles["Heading3"])
    invoice_issued_date = Paragraph(f"Invoice Date: {invoice.issued_at.strftime('%Y-%m-%d')}")
    elements.extend([invoice_id_para, invoice_issued_date, Spacer(1, 35)])

    # Table data
    data = [
        ["Item", "Description", "Amount"],
        [f"{invoice.invoice_id}", "Package details", f"KES {invoice.amount:,.2f}"],
        ["Total", "", f"KES {invoice.amount:,.2f}"],
    ]

    table = Table(data, colWidths=[100, 250, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    # Add footer note
    elements.append(Spacer(1, 30))  # ~30px margin
    center_style = styles["Normal"].clone("center_style")
    center_style.alignment = TA_CENTER
    center_style.fontSize = 9
    generated_on = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer_note = Paragraph(f"PDF generated on {generated_on}", center_style)
    elements.append(footer_note)

    # Build PDF with status strip
    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: draw_status(canvas, doc, getattr(invoice, "status", "unpaid")),
        onLaterPages=lambda canvas, doc: draw_status(canvas, doc, getattr(invoice, "status", "unpaid")),
    )

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice_{invoice.invoice_id}.pdf"'
    return response





@method_decorator(csrf_exempt, name='dispatch')
class PaymentCallbackView(APIView):
    def post(self, request, *args, **kwargs):

        # get fileds
        payment_date = request.data.get("payment_date")
        payment_time = request.data.get("payment_time")
        customer_name = request.data.get("customer_name")
        phone_number = request.data.get("phone_number")
        payment_amount = request.data.get("payment_amount")
        payment_description = request.data.get("payment_description")
        mpesa_receipt_number = request.data.get("mpesa_receipt_number")


        try:
            invoice = Invoice.objects.get(invoice_id=payment_description)
            invoice.status = "paid"
            invoice.save()

            # Package update
            package = invoice.package
            package.is_paid = True
            package.save()

            _schedule_driver_notification(package)

            # register the payment
            Payment.objects.create(
                invoice_id=invoice,
                amount=payment_amount,
                transaction_code=mpesa_receipt_number,
                customer_name=customer_name,
                phone_number=phone_number
            )
            

            # payment logs
            PaymentsLog.objects.create(invoice_id=invoice, data=request.data)

            return Response({"success": True, "message": "Payment updated."})
        
        except  Invoice.DoesNotExist:
            return Response({"success": False, "message": "Invoice not found."}, status=404)


        


