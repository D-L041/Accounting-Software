from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from billing.models import SchoolBillingSettings
from ledger.models import Account, FinancialPeriod, JournalEntry
from .models import Expense, ExpenseCategory


class ExpensePostingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="accountant", password="test-password")
        self.school = School.objects.create(name="Test School", code="expense-test-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
        self.period = FinancialPeriod.objects.create(school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31")
        self.expense_account = Account.objects.create(school=self.school, code="5000", name="Repairs", category="EXPENSE")
        self.cash = Account.objects.create(school=self.school, code="1000", name="Cash", category="ASSET")
        self.bank = Account.objects.create(school=self.school, code="1010", name="Bank", category="ASSET")
        self.mpesa = Account.objects.create(school=self.school, code="1020", name="M-Pesa", category="ASSET")
        self.ar = Account.objects.create(school=self.school, code="1200", name="Receivables", category="ASSET")
        SchoolBillingSettings.objects.create(school=self.school, receivables_account=self.ar, cash_account=self.cash, bank_account=self.bank, mpesa_account=self.mpesa)
        self.category = ExpenseCategory.objects.create(school=self.school, code="REPAIRS", name="Repairs", expense_account=self.expense_account)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_posting_expense_creates_balanced_journal(self):
        response = self.client.post(f"/api/schools/{self.school.pk}/expenses/expenses/", {
            "category": self.category.pk, "period": self.period.pk, "expense_date": "2026-03-02",
            "description": "Bus repair", "amount": "12500.00", "payment_method": "MPESA",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        expense_id = response.data["id"]
        posted = self.client.post(f"/api/schools/{self.school.pk}/expenses/expenses/{expense_id}/post/", {}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        self.assertEqual(posted.data["status"], Expense.Status.POSTED)
        journal = JournalEntry.objects.get(pk=posted.data["journal_entry"])
        self.assertTrue(journal.posted)
        self.assertEqual(sum(line.debit for line in journal.lines.all()), sum(line.credit for line in journal.lines.all()))
        self.assertEqual(journal.lines.get(credit__gt=0).account_id, self.mpesa.pk)

    def test_viewer_cannot_create_expense(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role="VIEWER")
        response = self.client.post(f"/api/schools/{self.school.pk}/expenses/expenses/", {
            "category": self.category.pk, "period": self.period.pk, "expense_date": "2026-03-02",
            "description": "Not permitted", "amount": "100.00", "payment_method": "CASH",
        }, format="json")
        self.assertEqual(response.status_code, 403)
