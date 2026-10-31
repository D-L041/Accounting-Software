from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from .models import Account, FinancialPeriod, JournalEntry, JournalLine
from .services import build_trial_balance


class JournalPostingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="not-for-production"
        )
        self.school = School.objects.create(name="Ledger Test School", code="ledger-test-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
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

    def test_api_can_create_and_post_a_balanced_journal(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            f"/api/schools/{self.school.pk}/ledger/journals/",
            {
                "reference": "API-JRN-001",
                "description": "Fees received",
                "entry_date": "2026-06-01",
                "period": self.period.pk,
                "lines": [
                    {"account": self.cash.pk, "description": "Cash received", "debit": "250.00", "credit": "0.00"},
                    {"account": self.fees.pk, "description": "Fee income", "debit": "0.00", "credit": "250.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        journal_id = response.data["id"]
        posted = client.post(
            f"/api/schools/{self.school.pk}/ledger/journals/{journal_id}/post/",
            {},
            format="json",
        )
        self.assertEqual(posted.status_code, 200, posted.data)
        self.assertTrue(posted.data["posted"])

    def test_api_rejects_unbalanced_journal_posting(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            f"/api/schools/{self.school.pk}/ledger/journals/",
            {
                "reference": "API-JRN-002",
                "description": "Unbalanced test",
                "entry_date": "2026-06-01",
                "period": self.period.pk,
                "lines": [
                    {"account": self.cash.pk, "debit": "250.00", "credit": "0.00"},
                    {"account": self.fees.pk, "debit": "0.00", "credit": "200.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        posted = client.post(
            f"/api/schools/{self.school.pk}/ledger/journals/{response.data['id']}/post/",
            {},
            format="json",
        )
        self.assertEqual(posted.status_code, 400)
        self.assertFalse(JournalEntry.objects.get(pk=response.data["id"]).posted)

    def test_api_does_not_expose_another_schools_accounts(self):
        other_school = School.objects.create(name="Hidden School", code="hidden-school")
        Account.objects.create(school=other_school, code="1000", name="Private Cash", category="ASSET")
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f"/api/schools/{self.school.pk}/ledger/accounts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["code"] for row in response.data}, {"1000", "4000"})

    def test_viewer_cannot_create_ledger_entries(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role="VIEWER")
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            f"/api/schools/{self.school.pk}/ledger/journals/",
            {
                "reference": "API-JRN-003",
                "description": "Viewer should not post",
                "entry_date": "2026-06-01",
                "period": self.period.pk,
                "lines": [
                    {"account": self.cash.pk, "debit": "10.00", "credit": "0.00"},
                    {"account": self.fees.pk, "debit": "0.00", "credit": "10.00"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class TrialBalanceApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="report-user", password="not-for-production")
        self.school = School.objects.create(name="Report School", code="report-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="ACCOUNTANT")
        self.period = FinancialPeriod.objects.create(school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31")
        self.cash = Account.objects.create(school=self.school, code="1000", name="Cash", category="ASSET")
        self.income = Account.objects.create(school=self.school, code="4000", name="Fees", category="INCOME")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_trial_balance_api_returns_posted_activity(self):
        entry = JournalEntry.objects.create(school=self.school, reference="TB-001", description="Test", period=self.period, created_by=self.user)
        JournalLine.objects.create(entry=entry, account=self.cash, debit=Decimal("125.00"))
        JournalLine.objects.create(entry=entry, account=self.income, credit=Decimal("125.00"))
        entry.post()
        response = self.client.get(f"/api/schools/{self.school.pk}/ledger/reports/trial-balance/?period={self.period.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_debits"], Decimal("125.00"))
        self.assertTrue(response.data["is_balanced"])

    def test_trial_balance_api_rejects_other_school_period(self):
        other = School.objects.create(name="Other Report School", code="other-report-school")
        other_period = FinancialPeriod.objects.create(school=other, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31")
        response = self.client.get(f"/api/schools/{self.school.pk}/ledger/reports/trial-balance/?period={other_period.pk}")
        self.assertEqual(response.status_code, 404)
