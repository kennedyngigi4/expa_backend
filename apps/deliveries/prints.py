from io import BytesIO
from datetime import datetime
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.units import inch
from django.core.files.storage import default_storage
from apps.deliveries.models import Shipment, Package

from io import BytesIO
from datetime import datetime
from django.http import HttpResponse
from django.core.files.storage import default_storage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch

def generate_shipment_pdf(request):
    ids = request.GET.get("ids")
    if not ids:
        return HttpResponse("No shipment IDs provided", status=400)

    shipment_ids = [s.strip() for s in ids.split(",") if s.strip()]
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="TitleStyle", parent=styles["Heading1"],
        alignment=TA_CENTER, spaceAfter=15
    )
    label_style = ParagraphStyle(
        name="Label", parent=styles["Normal"],
        alignment=TA_LEFT, spaceAfter=5, fontSize=10
    )
    center_style = ParagraphStyle(
        name="Center", parent=styles["Normal"], alignment=TA_CENTER
    )

    elements = []

    shipments = (
        Shipment.objects.filter(id__in=shipment_ids)
        .prefetch_related("shipmentpackage_set__package", "stages")
        .select_related("courier", "manager", "origin_office", "destination_office")
    )

    for shipment in shipments:
        # Title
        elements.append(Paragraph("Express Parcel - Manifest Details", title_style))
        elements.append(Spacer(1, 5))

        # QR Code (if available)
        if shipment.qrcode_svg and default_storage.exists(shipment.qrcode_svg.name):
            qr_path = shipment.qrcode_svg.path
            elements.append(Image(qr_path, width=1.5 * inch, height=1.5 * inch))
            elements.append(Spacer(1, 10))

        # Shipment details stacked vertically
        detail_lines = [
            f"<b>Manifest ID:</b> {shipment.shipment_id}",
            f"<b>Type:</b> {shipment.get_shipment_type_display()}",
            f"<b>Status:</b> {shipment.status.title()}",
            f"<b>Manager:</b> {getattr(shipment.manager, 'full_name', 'N/A')}",
            f"<b>Courier:</b> {getattr(shipment.courier, 'full_name', 'N/A')}",
            f"<b>Origin Office:</b> {getattr(shipment.origin_office, 'name', shipment.pickup_location or 'N/A')}",
            f"<b>Destination:</b> {getattr(shipment.destination_office, 'name', shipment.destination_location or 'N/A')}",
            f"<b>Created:</b> {shipment.assigned_at.strftime('%Y-%m-%d %H:%M')}",
        ]

        for line in detail_lines:
            elements.append(Paragraph(line, label_style))

        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<b>Waybills in this Manifest</b>", styles["Heading4"]))
        elements.append(Spacer(1, 5))

        pkg_data = [[
            "Waybill ID",
            "Sender",
            "Receiver",
            "Destination",
            "Status",
        ]]

        for sp in shipment.shipmentpackage_set.all():
            pkg = sp.package
            pkg_data.append([
                Paragraph(str(pkg.package_id), styles["Normal"]),
                Paragraph(getattr(pkg.sender_user, "full_name", "N/A"), styles["Normal"]),
                Paragraph(getattr(pkg.recipient_name, "full_name", "N/A"), styles["Normal"]),
                Paragraph(pkg.recipient_address or "N/A", styles["Normal"]),
                Paragraph(sp.status.title(), styles["Normal"]),
            ])

        # Wider destination column (150 pts ≈ 2 inches)
        package_table = Table(pkg_data, colWidths=[100, 80, 90, 150, 70])
        package_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),  # ensures multi-line text aligns nicely
        ]))

        elements.append(package_table)

        elements.append(Spacer(1, 15))
        elements.append(Paragraph(f"Generated on {datetime.now():%Y-%m-%d %H:%M}", center_style))
        elements.append(PageBreak())

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="shipments.pdf"'
    return response







def generate_package_pdf(request):
    ids = request.GET.get("ids")

    if not ids:
        return HttpResponse("No package IDs provided", status=400)

    package_ids = [s.strip() for s in ids.split(",") if s.strip()]
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="TitleStyle", parent=styles["Heading1"],
        alignment=TA_CENTER, spaceAfter=15
    )
    label_style = ParagraphStyle(
        name="Label", parent=styles["Normal"],
        alignment=TA_LEFT, spaceAfter=5, fontSize=10, leading=14
    )
    center_style = ParagraphStyle(
        name="Center", parent=styles["Normal"], alignment=TA_CENTER
    )

    elements = []
    packages = Package.objects.filter(id__in=package_ids).select_related("origin_office", "destination_office")

    for package in packages:
        # Title
        elements.append(Paragraph("Parcel Details", title_style))
        elements.append(Spacer(1, 5))

        # QR Code (if available)
        if package.qrcode_svg and default_storage.exists(package.qrcode_svg.name):
            qr_path = package.qrcode_svg.path
            elements.append(Image(qr_path, width=1.5 * inch, height=1.5 * inch))
            elements.append(Spacer(1, 10))

        # Details section — left-aligned column style
        details = [
            f"<b>Package ID:</b> {package.package_id}",
            f"<b>Sender Name:</b> {package.sender_name or 'N/A'}",
            f"<b>Sender Phone:</b> {package.sender_phone or 'N/A'}",
            f"<b>Sender Address:</b> {package.sender_address or 'N/A'}",
            f"<b>Recipient Name:</b> {package.recipient_name or 'N/A'}",
            f"<b>Recipient Phone:</b> {package.recipient_phone or 'N/A'}",
            f"<b>Recipient Address:</b> {package.recipient_address or 'N/A'}",
            f"<b>Delivery Type:</b> {package.get_delivery_type_display()}",
            f"<b>Weight:</b> {package.weight or 'N/A'} kg",
            f"<b>Size Category:</b> {getattr(package.size_category, 'name', 'N/A')}",
            f"<b>Created:</b> {package.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]

        for line in details:
            elements.append(Paragraph(line, label_style))

        elements.append(Spacer(1, 15))
        elements.append(Paragraph(f"Generated on {datetime.now():%Y-%m-%d %H:%M}", center_style))
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="packages.pdf"'
    return response





