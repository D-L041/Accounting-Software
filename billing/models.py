from decimal import Decimal

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
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["school", "invoice_number"], name="unique_invoice_number_school"),
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
        if errors:
            raise ValidationError(errors)

    @property
    def total_amount(self):
        return sum((line.amount for line in self.lines.all()), Decimal("0.00"))

    @property
    def amount_paid(self):
        return sum((allocation.amount for allocation in self.allocations.all()), Decimal("0.00"))

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
        ]

    def clean(self):
        super().clean()
        if self.student_id and self.student.school_id != self.school_id:
            raise ValidationError({"student": "Student must belong to this school."})

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
