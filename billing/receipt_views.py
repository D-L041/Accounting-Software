from io import BytesIO

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.views import APIView
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from accounts.models import School
from billing.models import Payment


class PaymentReceiptPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, school_pk, pk):
        school = get_object_or_404(
            School.objects.filter(
                memberships__user=request.user,
                memberships__is_active=True,
                is_active=True,
            ).distinct(),
            pk=school_pk,
        )
        payment = get_object_or_404(
            Payment.objects.filter(school=school).select_related("student", "journal_entry").prefetch_related("allocations__invoice"),
            pk=pk,
        )

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
            title=f"Receipt {payment.receipt_number}",
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle("ReceiptTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#17324d"))
        story = [
            Paragraph(school.name, title),
            Paragraph("OFFICIAL SCHOOL FEE RECEIPT", ParagraphStyle("ReceiptHeading", parent=styles["Heading2"], alignment=TA_CENTER)),
            Spacer(1, 8 * mm),
        ]
        details = [
            ["Receipt number", payment.receipt_number, "Date", payment.payment_date.strftime("%d %b %Y")],
            ["Student", payment.student.full_name, "Admission no.", payment.student.admission_number],
            ["Payment method", payment.get_method_display(), "Reference", payment.transaction_reference or "—"],
            ["Received amount", f"KES {payment.amount:,.2f}", "Recorded by", payment.journal_entry.created_by.get_username() if payment.journal_entry else "—"],
        ]
        table = Table(details, colWidths=[32 * mm, 58 * mm, 30 * mm, 52 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f7")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef3f7")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5df")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([table, Spacer(1, 8 * mm), Paragraph("Invoice allocations", styles["Heading3"])])
        allocation_data = [["Invoice number", "Invoice date", "Amount allocated"]]
        for allocation in payment.allocations.all():
            allocation_data.append([
                allocation.invoice.invoice_number,
                allocation.invoice.invoice_date.strftime("%d %b %Y"),
                f"KES {allocation.amount:,.2f}",
            ])
        allocations = Table(allocation_data, colWidths=[60 * mm, 45 * mm, 67 * mm], repeatRows=1)
        allocations.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5df")),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.extend([allocations, Spacer(1, 12 * mm), Paragraph("Thank you for your payment.", ParagraphStyle("Thanks", parent=styles["Normal"], alignment=TA_CENTER))])
        document.build(story)
        buffer.seek(0)
        return FileResponse(
            buffer, as_attachment=True, filename=f"{payment.receipt_number}.pdf",
            content_type="application/pdf",
        )
