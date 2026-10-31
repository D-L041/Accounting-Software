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

    def post(self, actor=None):
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
            from auditlog.services import record_event
            record_event(
                school=entry.school, actor=actor or entry.created_by, action="JOURNAL_POSTED",
                entity_type="JournalEntry", entity_id=entry.pk,
                summary=f"Posted journal {entry.reference}",
                metadata={"reference": entry.reference, "period": entry.period.name, "entry_date": entry.entry_date.isoformat()},
            )
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

class BankStatement(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECONCILED = "RECONCILED", "Reconciled"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="bank_statements")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="bank_statements")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="bank_statements")
    statement_start = models.DateField()
    statement_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-statement_end", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "account", "statement_end"],
                name="unique_bank_statement_end_per_account",
            ),
            models.CheckConstraint(
                condition=Q(statement_end__gte=models.F("statement_start")),
                name="bank_statement_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.account_id and (
            self.account.school_id != self.school_id
            or self.account.category != Account.Category.ASSET
        ):
            errors["account"] = "Choose an asset account belonging to this school."
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if self.statement_start and self.statement_end:
            statement_start = self._meta.get_field("statement_start").to_python(self.statement_start)
            statement_end = self._meta.get_field("statement_end").to_python(self.statement_end)
            if statement_end < statement_start:
                errors["statement_end"] = "Statement end must not precede its start."
            if self.period_id:
                period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
                period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
                if not (period_start <= statement_start and statement_end <= period_end):
                    errors["statement_start"] = "Statement dates must fall within the selected financial period."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk and BankStatement.objects.filter(pk=self.pk, status=self.Status.RECONCILED).exists():
            raise ValidationError("A reconciled bank statement is immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def statement_movement(self):
        return self.lines.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    @property
    def calculated_closing_balance(self):
        return self.opening_balance + self.statement_movement

    @property
    def is_statement_arithmetic_valid(self):
        return self.calculated_closing_balance == self.closing_balance

    def reconcile(self, actor=None):
        with transaction.atomic():
            statement = BankStatement.objects.select_for_update().get(pk=self.pk)
            if statement.status != self.Status.DRAFT:
                raise ValidationError("This bank statement has already been reconciled.")
            if not statement.lines.exists():
                raise ValidationError("Import at least one bank statement line before reconciling.")
            if statement.lines.filter(matched_journal_line__isnull=True).exists():
                raise ValidationError("Match every bank statement line to a posted ledger transaction first.")
            if not statement.is_statement_arithmetic_valid:
                raise ValidationError("Statement opening balance plus movements does not equal its closing balance.")
            statement.status = self.Status.RECONCILED
            statement.reconciled_at = timezone.now()
            statement.save(update_fields=["status", "reconciled_at"])
            from auditlog.services import record_event
            record_event(
                school=statement.school, actor=actor or statement.uploaded_by,
                action="BANK_STATEMENT_RECONCILED", entity_type="BankStatement",
                entity_id=statement.pk, summary=f"Reconciled bank statement ending {statement.statement_end}",
                metadata={"account_id": statement.account_id, "period_id": statement.period_id,
                          "statement_movement": str(statement.statement_movement)},
            )
            self.refresh_from_db()
            return self


class BankStatementLine(models.Model):
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name="lines")
    transaction_date = models.DateField()
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)
    # Positive values are deposits/credits to the bank; negative values are withdrawals/debits.
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    matched_journal_line = models.OneToOneField(
        JournalLine, null=True, blank=True, on_delete=models.PROTECT,
        related_name="matched_bank_statement_line",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["transaction_date", "id"]
        constraints = [
            models.CheckConstraint(condition=~Q(amount=0), name="bank_statement_line_nonzero"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.statement_id and not (
            self.statement.statement_start <= self.transaction_date <= self.statement.statement_end
        ):
            errors["transaction_date"] = "Transaction date must fall within the statement dates."
        if self.matched_journal_line_id:
            journal_line = self.matched_journal_line
            if journal_line.account_id != self.statement.account_id:
                errors["matched_journal_line"] = "Match a transaction posted to this bank account."
            elif not journal_line.entry.posted:
                errors["matched_journal_line"] = "Only posted ledger transactions can be matched."
            else:
                ledger_amount = journal_line.debit - journal_line.credit
                if ledger_amount != self.amount:
                    errors["matched_journal_line"] = "Statement amount must equal the signed ledger movement."
                if journal_line.entry.entry_date != self.transaction_date:
                    errors["matched_journal_line"] = "Statement and ledger transaction dates must match."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.statement_id and self.statement.status == BankStatement.Status.RECONCILED:
            raise ValidationError("Lines on a reconciled bank statement are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.statement.status == BankStatement.Status.RECONCILED:
            raise ValidationError("Lines on a reconciled bank statement cannot be deleted.")
        return super().delete(*args, **kwargs)

