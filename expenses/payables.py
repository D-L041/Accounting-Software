from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from auditlog.services import record_event
from ledger.models import JournalEntry, JournalLine

from .models import SupplierBill, SupplierBillPayment


@transaction.atomic
def submit_supplier_bill(bill_id, user):
    bill = SupplierBill.objects.select_for_update().select_related("school", "period").get(pk=bill_id)
    if bill.status != SupplierBill.Status.DRAFT:
        raise ValidationError("Only draft supplier bills can be submitted.")
    if bill.period.is_locked:
        raise ValidationError("Cannot submit a bill into a locked financial period.")
    bill.status = SupplierBill.Status.SUBMITTED
    bill.submitted_by = user
    bill.submitted_at = timezone.now()
    bill.save(update_fields=["status", "submitted_by", "submitted_at"])
    record_event(
        school=bill.school, actor=user, action="SUPPLIER_BILL_SUBMITTED",
        entity_type="SupplierBill", entity_id=bill.pk,
        summary=f"Submitted supplier bill {bill.bill_number} for approval",
        metadata={"amount": str(bill.amount), "supplier_id": bill.supplier_id},
    )
    return bill


@transaction.atomic
def approve_supplier_bill(bill_id, user):
    bill = SupplierBill.objects.select_for_update().select_related("school", "period").get(pk=bill_id)
    if bill.status != SupplierBill.Status.SUBMITTED:
        raise ValidationError("Only submitted supplier bills can be approved.")
    if bill.submitted_by_id == user.pk:
        raise ValidationError("The person who submitted a bill cannot approve the same bill.")
    if bill.period.is_locked:
        raise ValidationError("Cannot approve a bill in a locked financial period.")
    bill.status = SupplierBill.Status.APPROVED
    bill.approved_by = user
    bill.approved_at = timezone.now()
    bill.save(update_fields=["status", "approved_by", "approved_at"])
    record_event(
        school=bill.school, actor=user, action="SUPPLIER_BILL_APPROVED",
        entity_type="SupplierBill", entity_id=bill.pk,
        summary=f"Approved supplier bill {bill.bill_number}",
        metadata={"amount": str(bill.amount), "submitted_by_id": bill.submitted_by_id},
    )
    return bill


@transaction.atomic
def post_supplier_bill(bill_id, user):
    bill = SupplierBill.objects.select_for_update().select_related(
        "school", "supplier", "category__expense_account", "payable_account", "period"
    ).get(pk=bill_id)
    if bill.status != SupplierBill.Status.APPROVED:
        raise ValidationError("Only approved supplier bills can be posted.")
    if bill.period.is_locked:
        raise ValidationError("Cannot post a bill into a locked financial period.")
    if not (bill.period.starts_on <= bill.bill_date <= bill.period.ends_on):
        raise ValidationError("Bill date must fall within its financial period.")
    journal = JournalEntry.objects.create(
        school=bill.school, reference=f"BILL-{bill.bill_number}",
        description=f"Supplier bill {bill.bill_number}: {bill.description}",
        entry_date=bill.bill_date, period=bill.period, created_by=user,
    )
    JournalLine.objects.create(
        entry=journal, account=bill.category.expense_account,
        description=bill.description, debit=bill.amount,
    )
    JournalLine.objects.create(
        entry=journal, account=bill.payable_account,
        description=f"Payable to {bill.supplier.name}", credit=bill.amount,
    )
    journal.post(actor=user)
    bill.journal_entry = journal
    bill.status = SupplierBill.Status.POSTED
    bill.save(update_fields=["journal_entry", "status"])
    record_event(
        school=bill.school, actor=user, action="SUPPLIER_BILL_POSTED",
        entity_type="SupplierBill", entity_id=bill.pk,
        summary=f"Posted supplier bill {bill.bill_number}",
        metadata={"amount": str(bill.amount), "journal_entry_id": journal.pk},
    )
    return bill


@transaction.atomic
def record_supplier_bill_payment(bill_id, user, *, payment_date, amount, payment_method, payment_account, period, reference=""):
    bill = SupplierBill.objects.select_for_update().select_related("school", "supplier").get(pk=bill_id)
    if bill.status not in (SupplierBill.Status.POSTED, SupplierBill.Status.PART_PAID):
        raise ValidationError("Payments can only be recorded against posted supplier bills.")
    if period.school_id != bill.school_id or payment_account.school_id != bill.school_id:
        raise ValidationError("Payment period and account must belong to the bill's school.")
    if period.is_locked:
        raise ValidationError("Cannot record a payment in a locked financial period.")
    if payment_account.category != "ASSET" or not payment_account.is_active:
        raise ValidationError("Choose an active cash, bank or M-Pesa asset account.")
    if not (period.starts_on <= payment_date <= period.ends_on):
        raise ValidationError("Payment date must fall within its financial period.")
    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")
    balance = bill.balance
    if amount > balance:
        raise ValidationError(f"Payment exceeds the outstanding bill balance of {balance}.")
    if payment_method not in ("CASH", "BANK", "MPESA"):
        raise ValidationError("Choose CASH, BANK or MPESA as the payment method.")
    payment = SupplierBillPayment.objects.create(
        bill=bill, period=period, payment_date=payment_date, amount=amount,
        payment_method=payment_method, payment_account=payment_account,
        reference=reference, recorded_by=user,
    )
    sequence = bill.payments.count()
    journal = JournalEntry.objects.create(
        school=bill.school, reference=f"BPAY-{bill.bill_number}-{sequence:03d}",
        description=f"Payment for supplier bill {bill.bill_number}",
        entry_date=payment_date, period=period, created_by=user,
    )
    JournalLine.objects.create(
        entry=journal, account=bill.payable_account,
        description=f"Settlement to {bill.supplier.name}", debit=amount,
    )
    JournalLine.objects.create(
        entry=journal, account=payment_account,
        description=f"{payment.get_payment_method_display()} payment {reference}".strip(),
        credit=amount,
    )
    journal.post(actor=user)
    payment.journal_entry = journal
    payment.save(update_fields=["journal_entry"])
    bill.status = SupplierBill.Status.PAID if amount == balance else SupplierBill.Status.PART_PAID
    bill.save(update_fields=["status"])
    record_event(
        school=bill.school, actor=user, action="SUPPLIER_BILL_PAYMENT_RECORDED",
        entity_type="SupplierBillPayment", entity_id=payment.pk,
        summary=f"Recorded payment against supplier bill {bill.bill_number}",
        metadata={"bill_id": bill.pk, "amount": str(amount), "journal_entry_id": journal.pk},
    )
    return payment
