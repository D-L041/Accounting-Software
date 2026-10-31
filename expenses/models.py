from decimal import Decimal
from django.conf import settings
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from accounts.models import School
from billing.models import Payment
from ledger.models import Account, FinancialPeriod, JournalEntry


class Supplier(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="suppliers")
    name = models.CharField(max_length=180)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    tax_pin = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["school", "name"], name="unique_supplier_name_school")]

    def __str__(self):
        return self.name


class ExpenseCategory(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="expense_categories")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    expense_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="expense_categories")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["school", "code"], name="unique_expense_category_code_school")]

    def clean(self):
        super().clean()
        if self.expense_account_id and (
            self.expense_account.school_id != self.school_id
            or self.expense_account.category != Account.Category.EXPENSE
        ):
            raise ValidationError({"expense_account": "Select an expense account belonging to this school."})

    def __str__(self):
        return self.name


class ExpenseQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if self.filter(status="POSTED").exists():
            raise ValidationError("Posted expenses cannot be changed through bulk updates.")
        return super().update(**kwargs)

    def delete(self):
        if self.filter(status="POSTED").exists():
            raise ValidationError("Posted expenses cannot be deleted.")
        return super().delete()


class Expense(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="expenses")
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="expenses")
    expense_number = models.CharField(max_length=40)
    expense_date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=8, choices=Payment.Method.choices)
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_expense")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ExpenseQuerySet.as_manager()

    class Meta:
        ordering = ["-expense_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["school", "expense_number"], name="unique_expense_number_school"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.supplier_id and self.supplier.school_id != self.school_id:
            errors["supplier"] = "Supplier must belong to this school."
        if self.category_id and self.category.school_id != self.school_id:
            errors["category"] = "Category must belong to this school."
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk and Expense.objects.filter(pk=self.pk, status=self.Status.POSTED).exists():
            raise ValidationError("Posted expenses are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.Status.POSTED:
            raise ValidationError("Posted expenses cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.expense_number

class SupplierBill(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted for approval"
        APPROVED = "APPROVED", "Approved"
        POSTED = "POSTED", "Posted"
        PART_PAID = "PART_PAID", "Part paid"
        PAID = "PAID", "Paid"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="supplier_bills")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="bills")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="supplier_bills")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="supplier_bills")
    payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="supplier_bills")
    bill_number = models.CharField(max_length=40)
    supplier_invoice_number = models.CharField(max_length=100)
    bill_date = models.DateField()
    due_date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_supplier_bills")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="submitted_supplier_bills")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_supplier_bills")
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_supplier_bill")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-bill_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["school", "bill_number"], name="unique_supplier_bill_number_school"),
            models.UniqueConstraint(fields=["school", "supplier", "supplier_invoice_number"], name="unique_supplier_invoice_number_school"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="supplier_bill_amount_positive"),
            models.CheckConstraint(condition=Q(due_date__gte=models.F("bill_date")), name="supplier_bill_due_after_date"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.supplier_id and self.supplier.school_id != self.school_id:
            errors["supplier"] = "Supplier must belong to this school."
        if self.category_id and self.category.school_id != self.school_id:
            errors["category"] = "Expense category must belong to this school."
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if self.payable_account_id and (
            self.payable_account.school_id != self.school_id
            or self.payable_account.category != Account.Category.LIABILITY
        ):
            errors["payable_account"] = "Choose a liability account belonging to this school."
        if self.bill_date and self.due_date and self.due_date < self.bill_date:
            errors["due_date"] = "Due date cannot be before bill date."
        if self.period_id and self.bill_date:
            bill_date = self._meta.get_field("bill_date").to_python(self.bill_date)
            period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
            period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
            if not (period_start <= bill_date <= period_end):
                errors["bill_date"] = "Bill date must fall within its financial period."
        if errors:
            raise ValidationError(errors)

    @property
    def amount_paid(self):
        return sum((payment.amount for payment in self.payments.all()), Decimal("0.00"))

    @property
    def balance(self):
        return self.amount - self.amount_paid

    def save(self, *args, **kwargs):
        if self.pk:
            existing = SupplierBill.objects.get(pk=self.pk)
            if existing.status != self.Status.DRAFT:
                allowed = {"status", "submitted_by", "submitted_at", "approved_by", "approved_at", "journal_entry"}
                update_fields = set(kwargs.get("update_fields") or [])
                if not update_fields or not update_fields.issubset(allowed):
                    raise ValidationError("Submitted, approved or posted supplier bills cannot be edited.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only draft supplier bills can be deleted.")
        return super().delete(*args, **kwargs)


class SupplierBillPayment(models.Model):
    bill = models.ForeignKey(SupplierBill, on_delete=models.PROTECT, related_name="payments")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="supplier_bill_payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=8, choices=Payment.Method.choices)
    payment_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="supplier_bill_payments")
    reference = models.CharField(max_length=100, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_supplier_bill_payment")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payment_date", "id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="supplier_bill_payment_amount_positive")]

    def clean(self):
        super().clean()
        errors = {}
        if self.bill_id and self.period_id and self.bill.school_id != self.period.school_id:
            errors["period"] = "Payment period must belong to the bill's school."
        if self.bill_id and self.payment_account_id and self.payment_account.school_id != self.bill.school_id:
            errors["payment_account"] = "Payment account must belong to the bill's school."
        if self.payment_account_id and self.payment_account.category != Account.Category.ASSET:
            errors["payment_account"] = "Choose a cash, bank or M-Pesa asset account."
        if self.period_id and self.payment_date:
            payment_date = self._meta.get_field("payment_date").to_python(self.payment_date)
            period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
            period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
            if not (period_start <= payment_date <= period_end):
                errors["payment_date"] = "Payment date must fall within its financial period."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            existing = SupplierBillPayment.objects.get(pk=self.pk)
            update_fields = set(kwargs.get("update_fields") or [])
            if existing.journal_entry_id or update_fields != {"journal_entry"} or not self.journal_entry_id:
                raise ValidationError("Supplier bill payments are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Supplier bill payments cannot be deleted; use an approved reversal.")

