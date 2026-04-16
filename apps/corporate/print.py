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
from apps.deliveries.models import Shipment, Package, PackageItem

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



def generate_package_pdf(request):
    ids = request.GET.get("ids")

    if not ids:
        return HttpResponse("No package IDs provided", status=400)

    package_ids = [s.strip() for s in ids.split(",") if s.strip()]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        spaceAfter=15
    )

    label_style = ParagraphStyle(
        name="Label",
        parent=styles["Normal"],
        alignment=TA_LEFT,
        spaceAfter=5,
        fontSize=10,
        leading=14
    )

    center_style = ParagraphStyle(
        name="Center",
        parent=styles["Normal"],
        alignment=TA_CENTER
    )

    section_title_style = ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading3"],
        alignment=TA_LEFT,
        spaceAfter=10
    )

    wrap_style = ParagraphStyle(
        name="WrapStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10
    )

    elements = []

    packages = Package.objects.filter(package_id__in=package_ids).select_related(
        "origin_office", "destination_office"
    )

    for package in packages:
        # Title
        elements.append(Paragraph("Waybill Details", title_style))
        elements.append(Spacer(1, 5))

        # QR Code
        if package.qrcode_svg and default_storage.exists(package.qrcode_svg.name):
            qr_path = package.qrcode_svg.path
            elements.append(Image(qr_path, width=1.5 * inch, height=1.5 * inch))
            elements.append(Spacer(1, 10))

        # Package Details
        details = [
            f"<b>Waybill ID:</b> {package.package_id}",
            f"<b>Sender Name:</b> {package.sender_name or 'N/A'}",
            f"<b>Sender Phone:</b> {package.sender_phone or 'N/A'}",
            f"<b>Sender Address:</b> {package.sender_address or 'N/A'}",
            f"<b>Delivery Type:</b> {package.get_delivery_type_display()}",
            f"<b>Weight:</b> {package.weight or 'N/A'} kg",
            f"<b>Created:</b> {package.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]

        for line in details:
            elements.append(Paragraph(line, label_style))

        elements.append(Spacer(1, 15))

        # ----------------------------
        # ITEMS SECTION (Corporate)
        # ----------------------------
        items = package.package_items.all()

        if items.exists():
            elements.append(Paragraph("Waybill Items", section_title_style))

            table_data = [[
                "#", "Destination", "Recipient", "Phone",
                "No. Items", "Weight", "Price"
            ]]

            for i, item in enumerate(items, start=1):
                table_data.append([
                    str(i),
                    Paragraph(item.destination or "N/A", wrap_style),
                    Paragraph(item.recipient_name or "N/A", wrap_style),
                    Paragraph(item.recipient_phone or "N/A", wrap_style),
                    str(item.no_items or "N/A"),
                    item.weight or "N/A",
                    item.price or "N/A",
                ])

            table = Table(table_data, colWidths=[20, 160, 80, 70, 55, 55, 70])

            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (4, 1), (6, -1), "CENTER"),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 15))

        else:
            elements.append(Paragraph("<b>Items:</b> No items recorded for this package.", label_style))
            elements.append(Spacer(1, 10))

        # Footer
        elements.append(Paragraph(f"Generated on {datetime.now():%Y-%m-%d %H:%M}", center_style))
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="packages.pdf"'
    return response





