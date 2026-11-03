from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from ledger.models import (
    Account, BankStatement, BankStatementLine, FinancialPeriod,
    JournalEntry, JournalLine,
)


class BankReconciliationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="bank-accountant", password="test-password"
        )
        self.school = School.objects.create(name="Bank Test School", code="bank-test-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY2026", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        self.bank = Account.objects.create(
            school=self.school, code="1010", name="Main Bank", category=Account.Category.ASSET
        )
        self.income = Account.objects.create(
            school=self.school, code="4000", name="Fees Income", category=Account.Category.INCOME
        )
        self.journal = JournalEntry.objects.create(
            school=self.school, reference="BANK-RECEIPT-001", description="Bank deposit",
            entry_date="2026-05-04", period=self.period, created_by=self.user,
        )
        self.bank_line = JournalLine.objects.create(
            entry=self.journal, account=self.bank, debit=Decimal("100.00")
        )
        JournalLine.objects.create(
            entry=self.journal, account=self.income, credit=Decimal("100.00")
        )
        self.journal.post(actor=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_statement(self, closing="600.00"):
        return BankStatement.objects.create(
            school=self.school, account=self.bank, period=self.period,
            statement_start="2026-05-01", statement_end="2026-05-31",
            opening_balance=Decimal("500.00"), closing_balance=Decimal(closing),
            uploaded_by=self.user,
        )

    def test_statement_line_can_be_matched_and_reconciled(self):
        statement = self.create_statement()
        line = BankStatementLine.objects.create(
            statement=statement, transaction_date="2026-05-04",
            description="School fees deposit", reference="DEP-001",
            amount=Decimal("100.00"),
        )
        line.matched_journal_line = self.bank_line
        line.save(update_fields=["matched_journal_line"])
        statement.reconcile(actor=self.user)
        statement.refresh_from_db()
        self.assertEqual(statement.status, BankStatement.Status.RECONCILED)
        self.assertIsNotNone(statement.reconciled_at)
        with self.assertRaises(ValidationError):
            statement.save()

    def test_reconciliation_rejects_unmatched_statement_lines(self):
        statement = self.create_statement()
        BankStatementLine.objects.create(
            statement=statement, transaction_date="2026-05-04",
            description="Unmatched deposit", amount=Decimal("100.00"),
        )
        with self.assertRaises(ValidationError):
            statement.reconcile(actor=self.user)

    def test_reconciliation_rejects_statement_arithmetic_difference(self):
        statement = self.create_statement(closing="610.00")
        line = BankStatementLine.objects.create(
            statement=statement, transaction_date="2026-05-04",
            description="School fees deposit", amount=Decimal("100.00"),
            matched_journal_line=self.bank_line,
        )
        with self.assertRaises(ValidationError):
            statement.reconcile(actor=self.user)

    def test_statement_line_cannot_match_wrong_amount(self):
        statement = self.create_statement()
        line = BankStatementLine(
            statement=statement, transaction_date="2026-05-04",
            description="Wrong amount", amount=Decimal("99.00"),
            matched_journal_line=self.bank_line,
        )
        with self.assertRaises(ValidationError):
            line.full_clean()

    def test_api_creates_statement_and_matches_posted_line(self):
        response = self.client.post(
            f"/api/schools/{self.school.pk}/ledger/bank-statements/",
            {
                "account": self.bank.pk,
                "period": self.period.pk,
                "statement_start": "2026-05-01",
                "statement_end": "2026-05-31",
                "opening_balance": "500.00",
                "closing_balance": "600.00",
                "lines": [{
                    "transaction_date": "2026-05-04",
                    "description": "School fees deposit",
                    "reference": "DEP-001",
                    "amount": "100.00",
                }],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        statement_id = response.data["id"]
        line_id = response.data["lines"][0]["id"]
        matched = self.client.post(
            f"/api/schools/{self.school.pk}/ledger/bank-statements/{statement_id}/match-line/",
            {"statement_line_id": line_id, "journal_line_id": self.bank_line.pk},
            format="json",
        )
        self.assertEqual(matched.status_code, 200, matched.data)
        reconciled = self.client.post(
            f"/api/schools/{self.school.pk}/ledger/bank-statements/{statement_id}/reconcile/",
            {}, format="json",
        )
        self.assertEqual(reconciled.status_code, 200, reconciled.data)
        self.assertEqual(reconciled.data["status"], BankStatement.Status.RECONCILED)

    def test_api_does_not_expose_another_school_statement(self):
        other = School.objects.create(name="Other School", code="bank-other-school")
        other_bank = Account.objects.create(
            school=other, code="1010", name="Other Bank", category=Account.Category.ASSET
        )
        other_statement = BankStatement.objects.create(
            school=other, account=other_bank,
            period=FinancialPeriod.objects.create(
                school=other, name="FY2026", starts_on="2026-01-01", ends_on="2026-12-31"
            ),
            statement_start="2026-05-01", statement_end="2026-05-31",
            opening_balance="0.00", closing_balance="0.00", uploaded_by=self.user,
        )
        response = self.client.get(
            f"/api/schools/{self.school.pk}/ledger/bank-statements/{other_statement.pk}/"
        )
        self.assertEqual(response.status_code, 404)
