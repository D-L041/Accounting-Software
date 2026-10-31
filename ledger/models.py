from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

class FinancialPeriod(models.Model):
    name = models.CharField(max_length=80, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_locked = models.BooleanField(default=False)
    def clean(self):
        if self.ends_on < self.starts_on:
            raise ValidationError("Financial period end must not precede its start.")

class Account(models.Model):
    class Category(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity/Fund"
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=12, choices=Category.choices)
    is_active = models.BooleanField(default=True)
    def __str__(self): return f"{self.code} — {self.name}"

class JournalEntry(models.Model):
    reference = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=255)
    entry_date = models.DateField(default=timezone.localdate)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT)
    posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def post(self):
        with transaction.atomic():
            entry = JournalEntry.objects.select_for_update().get(pk=self.pk)
            if entry.posted:
                raise ValidationError("Journal is already posted.")
            if entry.period.is_locked:
                raise ValidationError("Cannot post into a locked financial period.")
            lines = list(entry.lines.select_related("account"))
            if len(lines) < 2:
                raise ValidationError("A journal requires at least two lines.")
            debit = sum((line.debit for line in lines), start=0)
            credit = sum((line.credit for line in lines), start=0)
            if debit <= 0 or debit != credit:
                raise ValidationError("Journal debits and credits must be equal and greater than zero.")
            if any(line.debit < 0 or line.credit < 0 or (line.debit > 0 and line.credit > 0) or (line.debit == 0 and line.credit == 0) for line in lines):
                raise ValidationError("Each journal line must contain either a positive debit or a positive credit.")
            entry.posted = True
            entry.posted_at = timezone.now()
            entry.save(update_fields=["posted", "posted_at"])
            self.refresh_from_db()

    def save(self, *args, **kwargs):
        if self.pk and JournalEntry.objects.filter(pk=self.pk, posted=True).exists():
            raise ValidationError("Posted journals are immutable; use a reversal or adjustment.")
        super().save(*args, **kwargs)

class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, related_name="lines", on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(debit__gte=0), name="journal_debit_nonnegative"),
            models.CheckConstraint(condition=models.Q(credit__gte=0), name="journal_credit_nonnegative"),
        ]
    def save(self, *args, **kwargs):
        if self.entry_id and JournalEntry.objects.filter(pk=self.entry_id, posted=True).exists():
            raise ValidationError("Cannot change lines on a posted journal.")
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        if JournalEntry.objects.filter(pk=self.entry_id, posted=True).exists():
            raise ValidationError("Cannot delete lines on a posted journal.")
        return super().delete(*args, **kwargs)
