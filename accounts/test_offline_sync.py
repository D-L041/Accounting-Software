import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from expenses.models import Expense, ExpenseCategory
from ledger.models import Account, FinancialPeriod


class OfflineExpenseSyncTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="offline-accountant", password="test-password")
        self.school = School.objects.create(name="Offline Pilot School", code="offline-pilot-school")
        SchoolMembership.objects.create(
            school=self.school, user=self.user, role=SchoolMembership.Role.ACCOUNTANT
        )
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY2026", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        self.expense_account = Account.objects.create(
            school=self.school, code="5200", name="Repairs", category=Account.Category.EXPENSE
        )
        self.category = ExpenseCategory.objects.create(
            school=self.school, code="REPAIRS", name="Repairs", expense_account=self.expense_account
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/schools/{self.school.pk}/offline-sync/"
        self.key = str(uuid.uuid4())
        self.payload = {
            "supplier": None,
            "category": self.category.pk,
            "period": self.period.pk,
            "expense_date": "2026-10-30",
            "description": "Offline captured stationery purchase",
            "amount": "1250.00",
            "payment_method": "CASH",
            "reference": "PETTY-CASH-01",
        }

    def submit(self, payload=None, key=None):
        return self.client.post(
            self.url,
            {"idempotency_key": key or self.key, "payload": payload or self.payload},
            format="json",
        )

    def test_sync_creates_only_a_draft_and_records_idempotency_receipt(self):
        response = self.submit()
        self.assertEqual(response.status_code, 201, response.data)
        expense = Expense.objects.get(pk=response.data["expense_id"])
        self.assertEqual(expense.status, Expense.Status.DRAFT)
        self.assertIsNone(expense.journal_entry_id)

    def test_repeated_sync_is_idempotent(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["status"], "already_applied")
        self.assertEqual(Expense.objects.filter(school=self.school).count(), 1)

    def test_reusing_key_for_different_payload_returns_conflict(self):
        first = self.submit()
        changed = {**self.payload, "amount": "1300.00"}
        second = self.submit(payload=changed)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 409, second.data)
        self.assertEqual(Expense.objects.filter(school=self.school).count(), 1)

    def test_viewer_cannot_sync_expense_drafts(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role=SchoolMembership.Role.VIEWER)
        response = self.submit()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Expense.objects.filter(school=self.school).count(), 0)

    def test_cross_school_category_is_rejected(self):
        other_school = School.objects.create(name="Other School", code="other-offline-school")
        other_account = Account.objects.create(
            school=other_school, code="5200", name="Other Repairs", category=Account.Category.EXPENSE
        )
        other_category = ExpenseCategory.objects.create(
            school=other_school, code="REPAIRS", name="Repairs", expense_account=other_account
        )
        response = self.submit(payload={**self.payload, "category": other_category.pk})
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Expense.objects.filter(school=self.school).count(), 0)

    def test_missing_idempotency_key_is_rejected(self):
        response = self.client.post(self.url, {"payload": self.payload}, format="json")
        self.assertEqual(response.status_code, 400)
