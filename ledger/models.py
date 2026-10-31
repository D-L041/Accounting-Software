from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import School


class FinancialPeriod(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="financial_periods")
    name = models.CharField(max_length=80)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_locked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_financial_period_per_school"),
            models.CheckConstraint(condition=Q(ends_on__gte=models.F("starts_on")), name="financial_period_end_after_start"),
        ]

    def clean(self):
        super().clean()
        if self.ends_on < self.starts_on:
            raise ValidationError({"ends_on": "Period end must not precede its start."})

    def __str__(self):
        return f"{self.school.name} — {self.name}"


class Account(models.Model):
    class Category(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity/Fund"
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="chart_of_accounts")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=12, choices=Category.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "code"], name="unique_account_code_per_school"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class JournalEntryQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if self.filter(posted=True).exists():
            raise ValidationError("Posted journals cannot be changed through bulk updates.")
        return super().update(**kwargs)

    def delete(self):
        if self.filter(posted=True).exists():
            raise ValidationError("Posted journals cannot be deleted.")
        return super().delete()


class JournalEntry(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="journal_entries")
    reference = models.CharField(max_length=40)
    description = models.CharField(max_length=255)
    entry_date = models.DateField(default=timezone.localdate)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT)
    posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = JournalEntryQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "reference"], name="unique_journal_reference_per_school"),
        ]

    def clean(self):
        super().clean()
        if self.period_id and self.school_id and self.period.school_id != self.school_id:
            raise ValidationError({"period": "Financial period must belong to the same school."})

    def post(self):
        """Validate and atomically post a balanced, immutable journal."""
        with transaction.atomic():
            entry = JournalEntry.objects.select_for_update().select_related("period", "school").get(pk=self.pk)
            if entry.posted:
                raise ValidationError("Journal is already posted.")
            if entry.period.school_id != entry.school_id:
                raise ValidationError("Financial period must belong to the same school.")
            if entry.period.is_locked:
                raise ValidationError("Cannot post into a locked financial period.")
            if not (entry.period.starts_on <= entry.entry_date <= entry.period.ends_on):
                raise ValidationError("Journal date must fall within its financial period.")

            lines = list(entry.lines.select_related("account"))
            if len(lines) < 2:
                raise ValidationError("A journal requires at least two lines.")
            if any(line.account.school_id != entry.school_id for line in lines):
                raise ValidationError("All accounts must belong to the journal's school.")
            if any(not line.account.is_active for line in lines):
                raise ValidationError("Inactive accounts cannot be used in a new posting.")

            debit = sum((line.debit for line in lines), Decimal("0.00"))
            credit = sum((line.credit for line in lines), Decimal("0.00"))
            if debit <= 0 or debit != credit:
                raise ValidationError("Journal debits and credits must be equal and greater than zero.")
            for line in lines:
                if line.debit < 0 or line.credit < 0:
                    raise ValidationError("Journal amounts cannot be negative.")
                if (line.debit > 0) == (line.credit > 0):
                    raise ValidationError("Each journal line must contain either a debit or a credit, not both.")

            entry.posted = True
            entry.posted_at = timezone.now()
            entry.save(update_fields=["posted", "posted_at"])
            self.refresh_from_db()

    def save(self, *args, **kwargs):
        if self.pk and JournalEntry.objects.filter(pk=self.pk, posted=True).exists():
            raise ValidationError("Posted journals are immutable; use a reversal or adjustment.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.posted:
            raise ValidationError("Posted journals cannot be deleted; use a reversal.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.description}"


class JournalLineQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if self.filter(entry__posted=True).exists():
            raise ValidationError("Lines belonging to posted journals cannot be changed.")
        return super().update(**kwargs)

    def delete(self):
        if self.filter(entry__posted=True).exists():
            raise ValidationError("Lines belonging to posted journals cannot be deleted.")
        return super().delete()


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, related_name="lines", on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    objects = JournalLineQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(debit__gte=0), name="journal_debit_nonnegative"),
            models.CheckConstraint(condition=Q(credit__gte=0), name="journal_credit_nonnegative"),
            models.CheckConstraint(
                condition=(Q(debit__gt=0, credit=0) | Q(credit__gt=0, debit=0)),
                name="journal_line_exactly_one_side",
            ),
        ]

    def clean(self):
        super().clean()
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Journal amounts cannot be negative.")
        if (self.debit > 0) == (self.credit > 0):
            raise ValidationError("A journal line must have exactly one positive side.")
        if self.entry_id and self.account_id and self.entry.school_id != self.account.school_id:
            raise ValidationError("Journal account must belong to the same school as the journal.")

    def save(self, *args, **kwargs):
        if self.entry_id and JournalEntry.objects.filter(pk=self.entry_id, posted=True).exists():
            raise ValidationError("Cannot change lines on a posted journal.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if JournalEntry.objects.filter(pk=self.entry_id, posted=True).exists():
            raise ValidationError("Cannot delete lines on a posted journal.")
        return super().delete(*args, **kwargs)
