from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Account, FinancialPeriod, JournalEntry, JournalLine

class JournalPostingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="not-for-production")
        self.period = FinancialPeriod.objects.create(name="FY Test", starts_on="2026-01-01", ends_on="2026-12-31")
        self.cash = Account.objects.create(code="1000", name="Cash", category="ASSET")
        self.fees = Account.objects.create(code="4000", name="School Fees", category="INCOME")
    def make_entry(self, debit=Decimal("100.00"), credit=Decimal("100.00")):
        entry = JournalEntry.objects.create(reference="JRN-001", description="Test receipt", period=self.period, created_by=self.user)
        JournalLine.objects.create(entry=entry, account=self.cash, debit=debit)
        JournalLine.objects.create(entry=entry, account=self.fees, credit=credit)
        return entry
    def test_balanced_journal_posts(self):
        entry = self.make_entry()
        entry.post()
        entry.refresh_from_db()
        self.assertTrue(entry.posted)
    def test_unbalanced_journal_is_rejected(self):
        entry = self.make_entry(Decimal("100.00"), Decimal("90.00"))
        with self.assertRaises(ValidationError): entry.post()
    def test_posted_journal_is_immutable(self):
        entry = self.make_entry()
        entry.post()
        entry.description = "changed"
        with self.assertRaises(ValidationError): entry.save()
