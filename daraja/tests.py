import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, Client

from .models import C2BNotification
from .services import normalize_phone


class DarajaPhoneTests(SimpleTestCase):
    def test_normalizes_local_mobile_number(self):
        self.assertEqual(normalize_phone("0712345678"), "254712345678")

    def test_accepts_international_mobile_number(self):
        self.assertEqual(normalize_phone("+254 712 345 678"), "254712345678")

    def test_rejects_invalid_number(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            normalize_phone("12345")


class C2BCallbackTests(TestCase):
    def test_duplicate_confirmation_is_captured_once(self):
        client = Client()
        payload = {
            "TransID": "QWERTY12345", "TransAmount": "1000.00",
            "BillRefNumber": "INV-000001", "BusinessShortCode": "123456",
            "MSISDN": "254712345678", "TransTime": "20261031120000",
        }
        with patch.dict("os.environ", {"DARAJA_SHORTCODE": "123456"}):
            first = client.post(
                "/api/daraja/callbacks/c2b/confirmation/",
                data=json.dumps(payload), content_type="application/json",
            )
            second = client.post(
                "/api/daraja/callbacks/c2b/confirmation/",
                data=json.dumps(payload), content_type="application/json",
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(C2BNotification.objects.filter(transaction_id="QWERTY12345").count(), 1)
        self.assertEqual(C2BNotification.objects.get(transaction_id="QWERTY12345").status,
                         C2BNotification.Status.RECEIVED)


class C2BReconciliationTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from accounts.models import AcademicYear, School, SchoolMembership, Student
        from ledger.models import Account, FinancialPeriod
        from billing.models import FeeItem, SchoolBillingSettings

        self.user = get_user_model().objects.create_user(username="c2b-bursar", password="test-password")
        self.school = School.objects.create(name="C2B Test School", code="c2b-test")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
        self.year = AcademicYear.objects.create(school=self.school, name="2026", starts_on="2026-01-01", ends_on="2026-12-31")
        self.period = FinancialPeriod.objects.create(school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31")
        self.student = Student.objects.create(school=self.school, admission_number="C2B001", first_name="Test", last_name="Learner", admission_date="2026-01-05")
        self.ar = Account.objects.create(school=self.school, code="1200", name="Receivables", category="ASSET")
        self.cash = Account.objects.create(school=self.school, code="1000", name="Cash", category="ASSET")
        self.bank = Account.objects.create(school=self.school, code="1010", name="Bank", category="ASSET")
        self.mpesa = Account.objects.create(school=self.school, code="1020", name="M-Pesa Clearing", category="ASSET")
        self.income = Account.objects.create(school=self.school, code="4000", name="Tuition", category="INCOME")
        SchoolBillingSettings.objects.create(school=self.school, receivables_account=self.ar, cash_account=self.cash, bank_account=self.bank, mpesa_account=self.mpesa)
        self.fee = FeeItem.objects.create(school=self.school, code="TUITION", name="Tuition", income_account=self.income)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        created = self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/", {
            "student": self.student.pk, "academic_year": self.year.pk, "period": self.period.pk,
            "invoice_date": "2026-02-01", "due_date": "2026-02-15",
            "lines": [{"fee_item": self.fee.pk, "quantity": "1.00", "unit_amount": "15000.00"}],
        }, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.invoice_id = created.data["id"]
        issued = self.client.post(f"/api/schools/{self.school.pk}/billing/invoices/{self.invoice_id}/issue/", {}, format="json")
        self.assertEqual(issued.status_code, 200, issued.data)
        self.notification = C2BNotification.objects.create(
            transaction_id="C2BTEST123", business_shortcode="123456",
            bill_reference=created.data["invoice_number"], amount=Decimal("1000.00"),
            msisdn="254712345678", transaction_time="20261031120000",
        )

    def test_verified_statement_match_posts_normal_mpesa_receipt_and_ledger(self):
        from .services import reconcile_c2b_notification
        from billing.models import Payment

        result = reconcile_c2b_notification(
            notification_id=self.notification.pk, school=self.school, user=self.user,
            invoice_id=self.invoice_id, confirm_statement_match=True,
        )
        self.assertEqual(result.status, C2BNotification.Status.POSTED)
        self.assertEqual(result.payment.method, Payment.Method.MPESA)
        self.assertEqual(result.payment.transaction_reference, "C2BTEST123")
        self.assertTrue(result.payment.journal_entry.posted)
        self.assertEqual(result.payment.journal_entry.lines.get(debit__gt=0).debit, Decimal("1000.00"))
        self.assertEqual(result.matched_invoice_id, self.invoice_id)

    def test_reconciliation_requires_independent_statement_confirmation(self):
        from django.core.exceptions import ValidationError
        from .services import reconcile_c2b_notification

        with self.assertRaises(ValidationError):
            reconcile_c2b_notification(
                notification_id=self.notification.pk, school=self.school, user=self.user,
                invoice_id=self.invoice_id, confirm_statement_match=False,
            )
        self.assertEqual(C2BNotification.objects.get(pk=self.notification.pk).status, C2BNotification.Status.RECEIVED)

    def test_duplicate_invoice_reference_across_schools_is_blocked(self):
        from django.core.exceptions import ValidationError
        from accounts.models import School
        from billing.models import Invoice
        from .services import reconcile_c2b_notification

        other_school = School.objects.create(name="Another School", code="c2b-other")
        Invoice.objects.create(
            school=other_school, student_id=self.student.pk, academic_year_id=self.year.pk,
            period_id=self.period.pk, invoice_number=self.notification.bill_reference,
            invoice_date="2026-02-01", due_date="2026-02-15",
        )
        with self.assertRaises(ValidationError):
            reconcile_c2b_notification(
                notification_id=self.notification.pk, school=self.school, user=self.user,
                invoice_id=self.invoice_id, confirm_statement_match=True,
            )
        self.assertFalse(C2BNotification.objects.get(pk=self.notification.pk).payment_id)
