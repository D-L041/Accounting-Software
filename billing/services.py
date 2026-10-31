from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Student
from ledger.models import Account, JournalEntry, JournalLine
from auditlog.services import record_event

from .models import FeeSchedule, Invoice, InvoiceLine, Payment, PaymentAllocation, SchoolBillingSettings


def _next_number(model, school, prefix, field):
    # Lock the school row so concurrent requests cannot issue duplicate numbers.
    from accounts.models import School
    School.objects.select_for_update().get(pk=school.pk)
    last = model.objects.filter(school=school, **{f"{field}__startswith": f"{prefix}-"}).order_by("-id").first()
    sequence = 1
    if last:
        try:
            sequence = int(getattr(last, field).rsplit("-", 1)[1]) + 1
        except (ValueError, IndexError):
            raise ValidationError("The last document number is invalid; contact an administrator.")
    return f"{prefix}-{sequence:06d}"


@transaction.atomic
def issue_invoice(invoice_id, user):
    invoice = Invoice.objects.select_for_update().select_related("school", "period", "student").get(pk=invoice_id)
    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError("Only draft invoices can be issued.")
    if invoice.period.is_locked:
        raise ValidationError("Cannot issue an invoice into a locked financial period.")
    if not (invoice.period.starts_on <= invoice.invoice_date <= invoice.period.ends_on):
        raise ValidationError("Invoice date must fall within its financial period.")
    lines = list(invoice.lines.select_related("fee_item__income_account"))
    if not lines:
        raise ValidationError("An invoice must contain at least one fee line.")
    total = sum((line.amount for line in lines), Decimal("0.00"))
    if total <= 0:
        raise ValidationError("Invoice total must be greater than zero.")
    settings = SchoolBillingSettings.objects.select_related("receivables_account").filter(school=invoice.school).first()
    if settings is None:
        raise ValidationError("Configure school billing accounts before issuing invoices.")
    journal = JournalEntry.objects.create(
        school=invoice.school, reference=f"INV-{invoice.invoice_number}",
        description=f"Invoice {invoice.invoice_number} — {invoice.student}",
        entry_date=invoice.invoice_date, period=invoice.period, created_by=user,
    )
    JournalLine.objects.create(entry=journal, account=settings.receivables_account, description="Student receivable", debit=total)
    for line in lines:
        JournalLine.objects.create(
            entry=journal, account=line.fee_item.income_account,
            description=line.description or line.fee_item.name, credit=line.amount,
        )
    journal.post()
    invoice.journal_entry = journal
    invoice.status = Invoice.Status.ISSUED
    invoice.save(update_fields=["journal_entry", "status"])
    record_event(
        school=invoice.school, actor=user, action="INVOICE_ISSUED",
        entity_type="Invoice", entity_id=invoice.pk,
        summary=f"Issued invoice {invoice.invoice_number}",
        metadata={"invoice_number": invoice.invoice_number, "student_id": invoice.student_id, "amount": str(total), "journal_entry_id": journal.pk},
    )
    return invoice


@transaction.atomic
def record_payment(*, school, student, payment_date, method, amount, allocations, user, transaction_reference="", notes=""):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")
    if transaction_reference and Payment.objects.filter(
        school=school, method=method, transaction_reference=transaction_reference
    ).exists():
        raise ValidationError("This payment reference has already been recorded for this school.")
    settings = SchoolBillingSettings.objects.select_related("receivables_account", "cash_account", "bank_account", "mpesa_account").filter(school=school).first()
    if settings is None:
        raise ValidationError("Configure school billing accounts before recording payments.")
    allocation_total = sum((Decimal(str(item["amount"])).quantize(Decimal("0.01")) for item in allocations), Decimal("0.00"))
    if allocation_total != amount:
        raise ValidationError("Payment allocations must add up exactly to the payment amount.")
    if not allocations:
        raise ValidationError("Allocate the payment to at least one invoice.")
    invoices = {}
    invoice_ids = [item["invoice_id"] for item in allocations]
    if len(invoice_ids) != len(set(invoice_ids)):
        raise ValidationError("Each invoice may appear only once in a payment allocation.")
    for item in allocations:
        invoice = Invoice.objects.select_for_update().get(pk=item["invoice_id"], school=school, student=student)
        if invoice.status not in {Invoice.Status.ISSUED, Invoice.Status.PART_PAID}:
            raise ValidationError(f"Invoice {invoice.invoice_number} is not open for payment.")
        allocated = sum((a.amount for a in invoice.allocations.all()), Decimal("0.00"))
        allocation_amount = Decimal(str(item["amount"])).quantize(Decimal("0.01"))
        if allocation_amount <= 0 or allocation_amount > invoice.total_amount - allocated:
            raise ValidationError(f"Allocation exceeds the outstanding balance on {invoice.invoice_number}.")
        invoices[invoice.pk] = (invoice, allocation_amount)
    receipt = _next_number(Payment, school, settings.receipt_prefix, "receipt_number")
    payment = Payment.objects.create(
        school=school, student=student, receipt_number=receipt, payment_date=payment_date,
        method=method, amount=amount, transaction_reference=transaction_reference, notes=notes,
    )
    for invoice, allocation_amount in invoices.values():
        PaymentAllocation.objects.create(payment=payment, invoice=invoice, amount=allocation_amount)
    periods = {item[0].period_id for item in invoices.values()}
    if len(periods) != 1:
        raise ValidationError("A single receipt cannot allocate across different financial periods.")
    period = next(iter(invoices.values()))[0].period
    if period.is_locked or not (period.starts_on <= payment_date <= period.ends_on):
        raise ValidationError("Payment date must fall within an unlocked financial period.")
    cash_or_bank = settings.bank_account if method == Payment.Method.BANK else settings.mpesa_account if method == Payment.Method.MPESA else settings.cash_account
    journal = JournalEntry.objects.create(
        school=school, reference=f"RCT-{receipt}",
        description=f"Fee receipt {receipt} — {student}", entry_date=payment_date,
        period=period, created_by=user,
    )
    JournalLine.objects.create(entry=journal, account=cash_or_bank, description=f"{method} received", debit=amount)
    JournalLine.objects.create(entry=journal, account=settings.receivables_account, description="Student account allocation", credit=amount)
    journal.post()
    payment.journal_entry = journal
    payment.save(update_fields=["journal_entry"])
    for invoice, _ in invoices.values():
        paid = sum((a.amount for a in invoice.allocations.all()), Decimal("0.00"))
        invoice.status = Invoice.Status.PAID if paid >= invoice.total_amount else Invoice.Status.PART_PAID
        invoice.save(update_fields=["status"])
    record_event(
        school=school, actor=user, action="PAYMENT_RECEIVED",
        entity_type="Payment", entity_id=payment.pk,
        summary=f"Recorded receipt {receipt}",
        metadata={"receipt_number": receipt, "student_id": student.pk, "amount": str(amount), "method": method, "journal_entry_id": journal.pk, "allocations": [{"invoice_id": invoice.pk, "amount": str(allocated)} for invoice, allocated in invoices.values()]},
    )
    return payment



@transaction.atomic
def generate_fee_schedule_invoices(schedule_id, user):
    schedule = FeeSchedule.objects.select_for_update().select_related(
        "school", "academic_year", "classroom", "period"
    ).get(pk=schedule_id)
    if not schedule.is_active:
        raise ValidationError("This fee schedule is inactive.")
    if schedule.period.is_locked:
        raise ValidationError("Cannot generate invoices into a locked financial period.")
    if not (schedule.period.starts_on <= schedule.invoice_date <= schedule.period.ends_on):
        raise ValidationError("Fee schedule invoice date must fall within its financial period.")
    lines = list(schedule.lines.select_related("fee_item"))
    if not lines:
        raise ValidationError("Add at least one fee item before generating invoices.")

    students = list(
        Student.objects.select_for_update().filter(
            school=schedule.school,
            classroom=schedule.classroom,
            status=Student.Status.ACTIVE,
        ).order_by("id")
    )
    if not students:
        raise ValidationError("There are no active students in the selected class.")

    existing_student_ids = set(
        Invoice.objects.filter(school=schedule.school, fee_schedule=schedule)
        .values_list("student_id", flat=True)
    )
    settings = SchoolBillingSettings.objects.filter(school=schedule.school).first()
    prefix = settings.invoice_prefix if settings else "INV"
    generated = []
    skipped = 0
    for student in students:
        if student.pk in existing_student_ids:
            skipped += 1
            continue
        number = _next_number(Invoice, schedule.school, prefix, "invoice_number")
        invoice = Invoice.objects.create(
            school=schedule.school,
            student=student,
            academic_year=schedule.academic_year,
            period=schedule.period,
            invoice_number=number,
            invoice_date=schedule.invoice_date,
            due_date=schedule.due_date,
            fee_schedule=schedule,
            notes=f"Generated from {schedule.term_name} fee schedule",
        )
        for line in lines:
            InvoiceLine.objects.create(
                invoice=invoice,
                fee_item=line.fee_item,
                description=line.fee_item.name,
                quantity=Decimal("1.00"),
                unit_amount=line.amount,
                amount=line.amount,
            )
        generated.append(invoice.pk)

    record_event(
        school=schedule.school, actor=user, action="BULK_INVOICES_GENERATED",
        entity_type="FeeSchedule", entity_id=schedule.pk,
        summary=f"Generated {len(generated)} draft invoices for {schedule.classroom} — {schedule.term_name}",
        metadata={"generated_count": len(generated), "skipped_existing_count": skipped, "invoice_ids": generated},
    )
    return {"generated_count": len(generated), "skipped_existing_count": skipped, "invoice_ids": generated}
