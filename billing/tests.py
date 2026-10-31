from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AcademicYear, School, SchoolMembership, Student
from ledger.models import Account, FinancialPeriod, JournalEntry
from .models import FeeItem, Invoice, Payment, SchoolBillingSettings


class BillingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="bursar", password="test-password")
        self.school = School.objects.create(name="St Stephen School", code="st-stephen-fees")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
        self.year = AcademicYear.objects.create(school=self.school, name="2026", starts_on="2026-01-01", ends_on="2026-12-31")
        self.period = FinancialPeriod.objects.create(school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31")
        self.student = Student.objects.create(school=self.school, admission_number="SS001", first_name="Amina", last_name="Learner", admission_date="2026-01-05")
        self.ar = Account.objects.create(school=self.school, code="1200", name="Receivables", category="ASSET")
        self.cash = Account.objects.create(school=self.school, code="1000", name="Cash", category="ASSET")
        self.bank = Account.objects.create(school=self.school, code="1010", name="Bank", category="ASSET")
        self.mpesa = Account.objects.create(school=self.school, code="1020", name="M-Pesa Clearing", category="ASSET")
        self.income = Account.objects.create(school=self.school, code="4000", name="Tuition", category="INCOME")
        SchoolBillingSettings.objects.create(school=self.school, receivables_account=self.ar, cash_account=self.cash, bank_account=self.bank, mpesa_account=self.mpesa)
        self.fee = FeeItem.objects.create(school=self.school, code="TUITION", name="Tuition", income_account=self.income)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def make_invoice(self):
        response = self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/", {
            "student": self.student.pk, "academic_year": self.year.pk, "period": self.period.pk,
            "invoice_date": "2026-02-01", "due_date": "2026-02-15",
            "lines": [{"fee_item": self.fee.pk, "quantity": "1.00", "unit_amount": "15000.00"}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_invoice_issue_posts_double_entry(self):
        invoice = self.make_invoice()
        response = self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/issue/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        journal = JournalEntry.objects.get(pk=response.data["journal_entry"])
        self.assertTrue(journal.posted)
        self.assertEqual(sum(x.debit for x in journal.lines.all()), Decimal("15000.00"))
        self.assertEqual(sum(x.credit for x in journal.lines.all()), Decimal("15000.00"))

    def test_mpesa_receipt_allocates_payment_and_updates_balance(self):
        invoice = self.make_invoice()
        self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/issue/", {}, format="json")
        response = self.client.post(f"/api/schools/{self.school.pk}/billing/payments/", {
            "student": self.student.pk, "payment_date": "2026-02-03", "method": "MPESA",
            "amount": "5000.00", "transaction_reference": "MPESA-ABC",
            "allocations": [{"invoice_id": invoice["id"], "amount": "5000.00"}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        payment = Payment.objects.get(pk=response.data["id"])
        self.assertEqual(payment.journal_entry.lines.get(debit__gt=0).account_id, self.mpesa.pk)
        refreshed = self.client.get(f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/")
        self.assertEqual(refreshed.data["status"], Invoice.Status.PART_PAID)
        self.assertEqual(Decimal(refreshed.data["balance"]), Decimal("10000.00"))

    def test_overpayment_is_rejected_atomically(self):
        invoice = self.make_invoice()
        self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/issue/", {}, format="json")
        response = self.client.post(f"/api/schools/{self.school.pk}/billing/payments/", {
            "student": self.student.pk, "payment_date": "2026-02-03", "method": "CASH",
            "amount": "16000.00", "allocations": [{"invoice_id": invoice["id"], "amount": "16000.00"}],
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)
