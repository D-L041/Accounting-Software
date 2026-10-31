from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import School
from .models import Account, FinancialPeriod, JournalEntry, JournalLine
from .services import build_trial_balance


class JournalPostingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="not-for-production"
        )
        self.school = School.objects.create(name="Ledger Test School", code="ledger-test-school")
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY Test", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        self.cash = Account.objects.create(school=self.school, code="1000", name="Cash", category="ASSET")
        self.fees = Account.objects.create(school=self.school, code="4000", name="School Fees", category="INCOME")

    def make_entry(self, reference="JRN-001", debit=Decimal("100.00"), credit=Decimal("100.00"), entry_date="2026-06-01"):
        entry = JournalEntry.objects.create(
            school=self.school, reference=reference, description="Test receipt", entry_date=entry_date,
            period=self.period, created_by=self.user,
        )
        JournalLine.objects.create(entry=entry, account=self.cash, debit=debit)
        JournalLine.objects.create(entry=entry, account=self.fees, credit=credit)
        return entry

    def test_balanced_journal_posts(self):
        entry = self.make_entry()
        entry.post()
        entry.refresh_from_db()
        self.assertTrue(entry.posted)
        self.assertIsNotNone(entry.posted_at)

    def test_unbalanced_journal_is_rejected(self):
        entry = self.make_entry(debit=Decimal("100.00"), credit=Decimal("90.00"))
        with self.assertRaises(ValidationError):
            entry.post()

    def test_locked_period_rejects_posting(self):
        self.period.is_locked = True
        self.period.save()
        entry = self.make_entry()
        with self.assertRaises(ValidationError):
            entry.post()

    def test_journal_date_must_be_inside_period(self):
        entry = self.make_entry(entry_date="2027-01-01")
        with self.assertRaises(ValidationError):
            entry.post()

    def test_posted_journal_is_immutable(self):
        entry = self.make_entry()
        entry.post()
        entry.description = "changed"
        with self.assertRaises(ValidationError):
            entry.save()

    def test_posted_journal_cannot_be_deleted(self):
        entry = self.make_entry()
        entry.post()
        with self.assertRaises(ValidationError):
            entry.delete()

    def test_posted_journal_cannot_be_bulk_updated_or_deleted(self):
        entry = self.make_entry()
        entry.post()
        with self.assertRaises(ValidationError):
            JournalEntry.objects.filter(pk=entry.pk).update(description="tampered")
        with self.assertRaises(ValidationError):
            JournalEntry.objects.filter(pk=entry.pk).delete()

    def test_posted_lines_cannot_be_bulk_updated_or_deleted(self):
        entry = self.make_entry()
        entry.post()
        with self.assertRaises(ValidationError):
            JournalLine.objects.filter(entry=entry).update(description="tampered")
        with self.assertRaises(ValidationError):
            JournalLine.objects.filter(entry=entry).delete()

    def test_line_must_have_exactly_one_positive_side(self):
        entry = JournalEntry.objects.create(
            school=self.school, reference="JRN-002", description="Invalid line",
            period=self.period, created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            JournalLine.objects.create(
                entry=entry, account=self.cash,
                debit=Decimal("10.00"), credit=Decimal("10.00"),
            )

    def test_trial_balance_uses_posted_entries_only(self):
        posted = self.make_entry()
        posted.post()
        self.make_entry(reference="JRN-003")
        result = build_trial_balance(self.period)
        self.assertEqual(result["total_debits"], Decimal("100.00"))
        self.assertEqual(result["total_credits"], Decimal("100.00"))
        self.assertTrue(result["is_balanced"])
        self.assertEqual(len(result["accounts"]), 2)

    def test_journal_cannot_use_another_schools_period(self):
        other_school = School.objects.create(name="Other Ledger School", code="other-ledger-school")
        other_period = FinancialPeriod.objects.create(
            school=other_school, name="FY Test", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        with self.assertRaises(ValidationError):
            JournalEntry.objects.create(
                school=self.school, reference="JRN-CROSS-PERIOD", description="Invalid tenant",
                period=other_period, created_by=self.user,
            )

    def test_journal_line_cannot_use_another_schools_account(self):
        entry = JournalEntry.objects.create(
            school=self.school, reference="JRN-CROSS-ACCOUNT", description="Invalid tenant",
            period=self.period, created_by=self.user,
        )
        other_school = School.objects.create(name="Other Account School", code="other-account-school")
        other_cash = Account.objects.create(
            school=other_school, code="1000", name="Cash", category="ASSET"
        )
        with self.assertRaises(ValidationError):
            JournalLine.objects.create(entry=entry, account=other_cash, debit=Decimal("10.00"))
