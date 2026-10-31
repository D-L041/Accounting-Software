from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AcademicYear, ClassRoom, School, SchoolMembership, Student
from auditlog.models import AuditEvent
from ledger.models import Account, FinancialPeriod, JournalEntry, JournalLine
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
        self.assertTrue(AuditEvent.objects.filter(action="INVOICE_DRAFT_CREATED", entity_id=str(response.data["id"])).exists())
        return response.data

    def test_invoice_issue_posts_double_entry(self):
        invoice = self.make_invoice()
        response = self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/issue/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        journal = JournalEntry.objects.get(pk=response.data["journal_entry"])
        self.assertTrue(journal.posted)
        self.assertTrue(AuditEvent.objects.filter(action="INVOICE_ISSUED", entity_id=str(invoice["id"])).exists())
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
        self.assertTrue(AuditEvent.objects.filter(action="PAYMENT_RECEIVED", entity_id=str(payment.pk)).exists())
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


    def test_duplicate_mpesa_reference_is_rejected(self):
        invoice = self.make_invoice()
        self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/issue/", {}, format="json")
        payload = {
            "student": self.student.pk, "payment_date": "2026-02-03", "method": "MPESA",
            "amount": "1000.00", "transaction_reference": "MPESA-DUPLICATE",
            "allocations": [{"invoice_id": invoice["id"], "amount": "1000.00"}],
        }
        first = self.client.post(f"/api/schools/{self.school.pk}/billing/payments/", payload, format="json")
        second = self.client.post(f"/api/schools/{self.school.pk}/billing/payments/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Payment.objects.filter(transaction_reference="MPESA-DUPLICATE").count(), 1)


    def test_cashbook_shows_posted_cash_movements_only(self):
        posted = JournalEntry.objects.create(
            school=self.school, reference="CASH-001", description="Cash fee receipt",
            entry_date="2026-02-04", period=self.period, created_by=self.user,
        )
        JournalLine.objects.create(entry=posted, account=self.cash, description="Cash received", debit=Decimal("2500.00"))
        JournalLine.objects.create(entry=posted, account=self.ar, description="Receivable cleared", credit=Decimal("2500.00"))
        posted.post()
        draft = JournalEntry.objects.create(
            school=self.school, reference="CASH-002", description="Unposted cash draft",
            entry_date="2026-02-05", period=self.period, created_by=self.user,
        )
        JournalLine.objects.create(entry=draft, account=self.cash, debit=Decimal("900.00"))
        JournalLine.objects.create(entry=draft, account=self.ar, credit=Decimal("900.00"))
        response = self.client.get(
            f"/api/schools/{self.school.pk}/ledger/reports/cashbook/?period={self.period.pk}"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total_receipts"], Decimal("2500.00"))
        self.assertEqual(response.data["total_payments"], Decimal("0.00"))
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertFalse(response.data["opening_balance_included"])


    def test_class_term_fee_schedule_generates_draft_invoices_idempotently(self):
        classroom = ClassRoom.objects.create(
            school=self.school, academic_year=self.year, name="Grade 4", stream="A"
        )
        first = Student.objects.create(
            school=self.school, classroom=classroom, admission_number="SS002",
            first_name="Brian", last_name="Learner", admission_date="2026-01-05",
        )
        second = Student.objects.create(
            school=self.school, classroom=classroom, admission_number="SS003",
            first_name="Amina", last_name="Learner", admission_date="2026-01-05",
        )
        payload = {
            "academic_year": self.year.pk,
            "classroom": classroom.pk,
            "period": self.period.pk,
            "term_name": "Term 2",
            "invoice_date": "2026-05-01",
            "due_date": "2026-05-15",
            "lines": [{"fee_item": self.fee.pk, "amount": "15000.00"}],
        }
        created = self.client.post(
            f"/api/schools/{self.school.pk}/billing/fee-schedules/", payload, format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        generated = self.client.post(
            f"/api/schools/{self.school.pk}/billing/fee-schedules/{created.data['id']}/generate-invoices/",
            {}, format="json",
        )
        self.assertEqual(generated.status_code, 200, generated.data)
        self.assertEqual(generated.data["generated_count"], 2)
        invoices = Invoice.objects.filter(fee_schedule_id=created.data["id"]).order_by("student_id")
        self.assertEqual(invoices.count(), 2)
        self.assertEqual({invoice.student_id for invoice in invoices}, {first.pk, second.pk})
        self.assertTrue(all(invoice.status == Invoice.Status.DRAFT for invoice in invoices))
        self.assertTrue(all(invoice.total_amount == Decimal("15000.00") for invoice in invoices))
        repeated = self.client.post(
            f"/api/schools/{self.school.pk}/billing/fee-schedules/{created.data['id']}/generate-invoices/",
            {}, format="json",
        )
        self.assertEqual(repeated.status_code, 200, repeated.data)
        self.assertEqual(repeated.data["generated_count"], 0)
        self.assertEqual(repeated.data["skipped_existing_count"], 2)
        self.assertEqual(Invoice.objects.filter(fee_schedule_id=created.data["id"]).count(), 2)


    def test_payment_receipt_pdf_is_available_only_in_own_school(self):
        invoice = self.make_invoice()
        issued = self.client.post(
            f"/api/schools/{self.school.pk}/billing/invoices/{invoice['id']}/issue/", {}, format="json"
        )
        self.assertEqual(issued.status_code, 200, issued.data)
        payment = self.client.post(
            f"/api/schools/{self.school.pk}/billing/payments/",
            {
                "student": self.student.pk, "payment_date": "2026-02-03", "method": "CASH",
                "amount": "1000.00", "allocations": [{"invoice_id": invoice["id"], "amount": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        receipt = self.client.get(
            f"/api/schools/{self.school.pk}/billing/payments/{payment.data['id']}/receipt/"
        )
        self.assertEqual(receipt.status_code, 200)
        self.assertEqual(receipt["Content-Type"], "application/pdf")
        body = b"".join(receipt.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))
        other = School.objects.create(name="Private Receipt School", code="private-receipt-school")
        response = self.client.get(
            f"/api/schools/{other.pk}/billing/payments/{payment.data['id']}/receipt/"
        )
        self.assertEqual(response.status_code, 404)
