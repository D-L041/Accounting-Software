from decimal import Decimal

from django.conf import settings

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from accounts.models import School, Student
from ledger.models import Account, FinancialPeriod, JournalEntry


class FeeItem(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="fee_items")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    income_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="fee_items")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["school", "code"], name="unique_fee_item_code_school")]

    def clean(self):
        super().clean()
        if self.income_account_id and self.school_id:
            if self.income_account.school_id != self.school_id or self.income_account.category != Account.Category.INCOME:
                raise ValidationError({"income_account": "Select an income account belonging to this school."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.name}"


class SchoolBillingSettings(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="billing_settings")
    receivables_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="billing_receivables_settings")
    cash_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="billing_cash_settings")
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="billing_bank_settings")
    mpesa_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="billing_mpesa_settings")
    invoice_prefix = models.CharField(max_length=12, default="INV")
    receipt_prefix = models.CharField(max_length=12, default="RCT")

    def clean(self):
        super().clean()
        expected = [
            (self.receivables_account, Account.Category.ASSET, "receivables_account"),
            (self.cash_account, Account.Category.ASSET, "cash_account"),
            (self.bank_account, Account.Category.ASSET, "bank_account"),
            (self.mpesa_account, Account.Category.ASSET, "mpesa_account"),
        ]
        errors = {}
        for account, category, field in expected:
            if account and (account.school_id != self.school_id or account.category != category):
                errors[field] = "Select an asset account belonging to this school."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Billing settings — {self.school.name}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PART_PAID = "PART_PAID", "Part paid"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="invoices")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="invoices")
    academic_year = models.ForeignKey("accounts.AcademicYear", on_delete=models.PROTECT)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT)
    invoice_number = models.CharField(max_length=40)
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_invoice")
    fee_schedule = models.ForeignKey("FeeSchedule", null=True, blank=True, on_delete=models.PROTECT, related_name="generated_invoices")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["school", "invoice_number"], name="unique_invoice_number_school"),
            models.UniqueConstraint(fields=["school", "student", "fee_schedule"], condition=Q(fee_schedule__isnull=False), name="unique_student_fee_schedule_invoice"),
            models.CheckConstraint(condition=Q(due_date__gte=models.F("invoice_date")), name="invoice_due_after_issue"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.student_id and self.student.school_id != self.school_id:
            errors["student"] = "Student must belong to this school."
        if self.academic_year_id and self.academic_year.school_id != self.school_id:
            errors["academic_year"] = "Academic year must belong to this school."
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if self.fee_schedule_id and (
            self.fee_schedule.school_id != self.school_id
            or self.fee_schedule.classroom_id != self.student.classroom_id
            or self.fee_schedule.academic_year_id != self.academic_year_id
            or self.fee_schedule.period_id != self.period_id
        ):
            errors["fee_schedule"] = "Fee schedule must match the school, student class, academic year and financial period."
        if errors:
            raise ValidationError(errors)

    @property
    def gross_total_amount(self):
        return sum((line.amount for line in self.lines.all()), Decimal("0.00"))

    @property
    def total_amount(self):
        credits = sum((note.amount for note in self.credit_notes.filter(status=CreditNote.Status.POSTED)), Decimal("0.00"))
        return self.gross_total_amount - credits

    @property
    def amount_paid(self):
        allocations = sum((allocation.amount for allocation in self.allocations.all()), Decimal("0.00"))
        refunds = sum((refund.amount for refund in self.payment_refunds.all()), Decimal("0.00"))
        return allocations - refunds

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return self.invoice_number


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    fee_item = models.ForeignKey(FeeItem, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_amount = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="invoice_line_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_amount__gte=0), name="invoice_line_unit_amount_nonnegative"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="invoice_line_amount_nonnegative"),
        ]

    def clean(self):
        super().clean()
        if self.fee_item_id and self.invoice_id and self.fee_item.school_id != self.invoice.school_id:
            raise ValidationError({"fee_item": "Fee item must belong to the invoice's school."})
        if self.amount != (self.quantity * self.unit_amount).quantize(Decimal("0.01")):
            raise ValidationError({"amount": "Line amount must equal quantity multiplied by unit amount."})

    def save(self, *args, **kwargs):
        if self.invoice_id and self.invoice.status != Invoice.Status.DRAFT:
            raise ValidationError("Only draft invoices can be changed.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.invoice.status != Invoice.Status.DRAFT:
            raise ValidationError("Only draft invoice lines can be deleted.")
        return super().delete(*args, **kwargs)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK = "BANK", "Bank"
        MPESA = "MPESA", "M-Pesa"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="fee_payments")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="fee_payments")
    receipt_number = models.CharField(max_length=40)
    payment_date = models.DateField()
    method = models.CharField(max_length=8, choices=Method.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_reference = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_payment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["school", "receipt_number"], name="unique_receipt_number_school"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
            models.UniqueConstraint(fields=["school", "method", "transaction_reference"], condition=~Q(transaction_reference=""), name="unique_payment_external_ref_school"),
        ]

    def clean(self):
        super().clean()
        if self.student_id and self.student.school_id != self.school_id:
            raise ValidationError({"student": "Student must belong to this school."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.receipt_number


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_allocation_positive"),
            models.UniqueConstraint(fields=["payment", "invoice"], name="unique_payment_invoice_allocation"),
        ]

    def clean(self):
        super().clean()
        if self.payment_id and self.invoice_id:
            if self.payment.school_id != self.invoice.school_id or self.payment.student_id != self.invoice.student_id:
                raise ValidationError("Payment and invoice must belong to the same school and student.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class FeeSchedule(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="fee_schedules")
    academic_year = models.ForeignKey("accounts.AcademicYear", on_delete=models.PROTECT, related_name="fee_schedules")
    classroom = models.ForeignKey("accounts.ClassRoom", on_delete=models.PROTECT, related_name="fee_schedules")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="fee_schedules")
    term_name = models.CharField(max_length=40)
    invoice_date = models.DateField()
    due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-academic_year__starts_on", "classroom__name", "term_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "academic_year", "classroom", "term_name"], name="unique_class_term_fee_schedule"),
            models.CheckConstraint(condition=Q(due_date__gte=models.F("invoice_date")), name="fee_schedule_due_after_invoice"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.academic_year_id and self.academic_year.school_id != self.school_id:
            errors["academic_year"] = "Academic year must belong to this school."
        if self.classroom_id and (self.classroom.school_id != self.school_id or self.classroom.academic_year_id != self.academic_year_id):
            errors["classroom"] = "Class must belong to this school and academic year."
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if self.period_id and not (self.period.starts_on <= self.invoice_date <= self.period.ends_on):
            errors["invoice_date"] = "Invoice date must fall within the financial period."
        if self.due_date < self.invoice_date:
            errors["due_date"] = "Due date cannot precede invoice date."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.classroom} — {self.term_name} — {self.academic_year}"


class FeeScheduleLine(models.Model):
    schedule = models.ForeignKey(FeeSchedule, on_delete=models.CASCADE, related_name="lines")
    fee_item = models.ForeignKey(FeeItem, on_delete=models.PROTECT, related_name="schedule_lines")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["schedule", "fee_item"], name="unique_fee_item_per_schedule"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="fee_schedule_line_amount_positive"),
        ]

    def clean(self):
        super().clean()
        if self.fee_item_id and self.schedule_id and (
            self.fee_item.school_id != self.schedule.school_id or not self.fee_item.is_active
        ):
            raise ValidationError({"fee_item": "Fee item must be active and belong to the fee schedule's school."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class CreditNote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="credit_notes")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="credit_notes")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="credit_notes")
    credit_note_number = models.CharField(max_length=40)
    credit_date = models.DateField()
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=8, choices=Status.choices, default="DRAFT")
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_credit_note")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-credit_date", "-id"]
        constraints = [models.UniqueConstraint(fields=["school", "credit_note_number"], name="unique_credit_note_number_school")]

    @property
    def amount(self):
        return sum((line.amount for line in self.lines.all()), Decimal("0.00"))

    def clean(self):
        super().clean()
        errors = {}
        if self.invoice_id and self.invoice.school_id != self.school_id:
            errors["invoice"] = "Invoice must belong to this school."
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if self.period_id and self.credit_date:
            credit_date = self._meta.get_field("credit_date").to_python(self.credit_date)
            period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
            period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
            if not (period_start <= credit_date <= period_end):
                errors["credit_date"] = "Credit note date must fall within its financial period."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            existing = CreditNote.objects.get(pk=self.pk)
            if existing.status != self.Status.DRAFT:
                allowed = {"status", "journal_entry"}
                fields = set(kwargs.get("update_fields") or [])
                if not fields or not fields.issubset(allowed):
                    raise ValidationError("Posted credit notes are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != self.Status.DRAFT:
            raise ValidationError("Posted credit notes cannot be deleted.")
        return super().delete(*args, **kwargs)


class CreditNoteLine(models.Model):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name="lines")
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.PROTECT, related_name="credit_note_lines")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="credit_note_line_amount_positive")]

    def clean(self):
        super().clean()
        if self.credit_note_id and self.invoice_line_id:
            if self.invoice_line.invoice_id != self.credit_note.invoice_id:
                raise ValidationError({"invoice_line": "Credit note line must refer to a line on the selected invoice."})
            already_credited = CreditNoteLine.objects.filter(
                invoice_line_id=self.invoice_line_id,
                credit_note__status=CreditNote.Status.POSTED,
            ).exclude(pk=self.pk).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
            if self.amount + already_credited > self.invoice_line.amount:
                raise ValidationError({"amount": "Credit amount exceeds the uncredited value of this invoice line."})
            if self.credit_note.status != CreditNote.Status.DRAFT:
                raise ValidationError("Lines can only be added to draft credit notes.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.credit_note.status != CreditNote.Status.DRAFT:
            raise ValidationError("Lines on posted credit notes are immutable.")
        return super().delete(*args, **kwargs)


class PaymentRefund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payment_refunds")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="payment_refunds")
    payment_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payment_refunds")
    refund_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_payment_refund")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-refund_date", "-id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_refund_amount_positive")]

    def clean(self):
        super().clean()
        errors = {}
        if self.payment_id and self.invoice_id:
            if self.payment.school_id != self.invoice.school_id:
                errors["invoice"] = "Payment and invoice must belong to the same school."
            allocation = PaymentAllocation.objects.filter(payment=self.payment, invoice=self.invoice).first()
            if not allocation:
                errors["invoice"] = "The selected payment was not allocated to this invoice."
            else:
                refunded = PaymentRefund.objects.filter(payment=self.payment, invoice=self.invoice).exclude(
                    pk=self.pk
                ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
                if self.amount + refunded > allocation.amount:
                    errors["amount"] = "Refund exceeds the unrefunded amount allocated to this invoice."
        if self.period_id and self.payment_id and self.period.school_id != self.payment.school_id:
            errors["period"] = "Refund period must belong to the payment's school."
        if self.payment_account_id and self.payment_id and (
            self.payment_account.school_id != self.payment.school_id
            or self.payment_account.category != Account.Category.ASSET
        ):
            errors["payment_account"] = "Choose a cash, bank or M-Pesa asset account belonging to this school."
        if self.period_id and self.refund_date:
            refund_date = self._meta.get_field("refund_date").to_python(self.refund_date)
            period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
            period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
            if not (period_start <= refund_date <= period_end):
                errors["refund_date"] = "Refund date must fall within its financial period."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            existing = PaymentRefund.objects.get(pk=self.pk)
            fields = set(kwargs.get("update_fields") or [])
            if existing.journal_entry_id or fields != {"journal_entry"} or not self.journal_entry_id:
                raise ValidationError("Payment refunds are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Payment refunds cannot be deleted; use an approved reversal.")

