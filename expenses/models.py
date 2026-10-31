from decimal import Decimal

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

    def __str__(self):
        return self.expense_number
