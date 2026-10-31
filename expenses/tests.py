from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from auditlog.models import AuditEvent
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
        response = self.client.post(f"/api/schools/{self.school.pk}/expenses/", {
            "category": self.category.pk, "period": self.period.pk, "expense_date": "2026-03-02",
            "description": "Bus repair", "amount": "12500.00", "payment_method": "MPESA",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        expense_id = response.data["id"]
        self.assertTrue(AuditEvent.objects.filter(action="EXPENSE_CREATED", entity_id=str(expense_id)).exists())
        posted = self.client.post(f"/api/schools/{self.school.pk}/expenses/{expense_id}/post/", {}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        self.assertEqual(posted.data["status"], Expense.Status.POSTED)
        journal = JournalEntry.objects.get(pk=posted.data["journal_entry"])
        self.assertTrue(journal.posted)
        self.assertEqual(sum(line.debit for line in journal.lines.all()), sum(line.credit for line in journal.lines.all()))
        self.assertEqual(journal.lines.get(credit__gt=0).account_id, self.mpesa.pk)
        self.assertTrue(AuditEvent.objects.filter(action="EXPENSE_POSTED", entity_id=str(expense_id)).exists())

    def test_viewer_cannot_create_expense(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role="VIEWER")
        response = self.client.post(f"/api/schools/{self.school.pk}/expenses/", {
            "category": self.category.pk, "period": self.period.pk, "expense_date": "2026-03-02",
            "description": "Not permitted", "amount": "100.00", "payment_method": "CASH",
        }, format="json")
        self.assertEqual(response.status_code, 403)

class SupplierBillWorkflowTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from expenses.models import Supplier
        self.User = get_user_model()
        self.creator = self.User.objects.create_user(username="bill-creator", password="test-password")
        self.approver = self.User.objects.create_user(username="bill-approver", password="test-password")
        self.school = School.objects.create(name="Payables School", code="payables-school")
        SchoolMembership.objects.create(school=self.school, user=self.creator, role="ACCOUNTANT")
        SchoolMembership.objects.create(school=self.school, user=self.approver, role="ADMIN")
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        self.expense_account = Account.objects.create(
            school=self.school, code="5100", name="Repairs", category="EXPENSE"
        )
        self.payable_account = Account.objects.create(
            school=self.school, code="2000", name="Trade Payables", category="LIABILITY"
        )
        self.bank = Account.objects.create(
            school=self.school, code="1010", name="Bank", category="ASSET"
        )
        self.category = ExpenseCategory.objects.create(
            school=self.school, code="REPAIRS", name="Repairs", expense_account=self.expense_account
        )
        self.supplier = Supplier.objects.create(
            school=self.school, name="ABC Supplies", tax_pin="P000000001"
        )
        self.client = APIClient()

    def create_bill(self):
        from expenses.models import SupplierBill
        return SupplierBill.objects.create(
            school=self.school, supplier=self.supplier, category=self.category,
            period=self.period, payable_account=self.payable_account,
            bill_number="BILL-000001", supplier_invoice_number="ABC-INV-001",
            bill_date="2026-04-01", due_date="2026-04-30",
            description="Bus spare parts", amount="50000.00", created_by=self.creator,
        )

    def test_approval_separation_and_posting_create_payable(self):
        from django.core.exceptions import ValidationError
        from expenses.models import SupplierBill
        from expenses.payables import approve_supplier_bill, post_supplier_bill, submit_supplier_bill
        bill = self.create_bill()
        submit_supplier_bill(bill.pk, self.creator)
        with self.assertRaises(ValidationError):
            approve_supplier_bill(bill.pk, self.creator)
        approved = approve_supplier_bill(bill.pk, self.approver)
        self.assertEqual(approved.status, SupplierBill.Status.APPROVED)
        posted = post_supplier_bill(bill.pk, self.approver)
        self.assertEqual(posted.status, SupplierBill.Status.POSTED)
        journal = JournalEntry.objects.get(pk=posted.journal_entry_id)
        self.assertTrue(journal.posted)
        self.assertEqual(journal.lines.get(debit__gt=0).account_id, self.expense_account.pk)
        self.assertEqual(journal.lines.get(credit__gt=0).account_id, self.payable_account.pk)

    def test_partial_and_full_payments_reduce_payable(self):
        from expenses.models import SupplierBill, SupplierBillPayment
        from expenses.payables import approve_supplier_bill, post_supplier_bill, record_supplier_bill_payment, submit_supplier_bill
        bill = self.create_bill()
        submit_supplier_bill(bill.pk, self.creator)
        approve_supplier_bill(bill.pk, self.approver)
        bill = post_supplier_bill(bill.pk, self.approver)
        first = record_supplier_bill_payment(
            bill.pk, self.creator, payment_date=__import__("datetime").date(2026, 4, 10),
            amount="20000.00", payment_method="BANK", payment_account=self.bank,
            period=self.period, reference="TRX-001",
        )
        bill.refresh_from_db()
        self.assertEqual(bill.status, SupplierBill.Status.PART_PAID)
        self.assertEqual(bill.balance, __import__("decimal").Decimal("30000.00"))
        self.assertTrue(first.journal_entry.posted)
        second = record_supplier_bill_payment(
            bill.pk, self.creator, payment_date=__import__("datetime").date(2026, 4, 20),
            amount="30000.00", payment_method="BANK", payment_account=self.bank,
            period=self.period, reference="TRX-002",
        )
        bill.refresh_from_db()
        self.assertEqual(bill.status, SupplierBill.Status.PAID)
        self.assertEqual(bill.balance, __import__("decimal").Decimal("0.00"))
        self.assertEqual(SupplierBillPayment.objects.filter(bill=bill).count(), 2)
        self.assertTrue(second.journal_entry.posted)

    def test_payment_cannot_exceed_outstanding_balance(self):
        from django.core.exceptions import ValidationError
        from expenses.payables import approve_supplier_bill, post_supplier_bill, record_supplier_bill_payment, submit_supplier_bill
        bill = self.create_bill()
        submit_supplier_bill(bill.pk, self.creator)
        approve_supplier_bill(bill.pk, self.approver)
        post_supplier_bill(bill.pk, self.approver)
        with self.assertRaises(ValidationError):
            record_supplier_bill_payment(
                bill.pk, self.creator, payment_date=__import__("datetime").date(2026, 4, 10),
                amount="50001.00", payment_method="BANK", payment_account=self.bank,
                period=self.period,
            )

    def test_api_requires_owner_or_admin_to_approve_and_scopes_bills(self):
        from expenses.models import SupplierBill
        bill = self.create_bill()
        self.client.force_authenticate(self.creator)
        base = f"/api/schools/{self.school.pk}/expenses/bills/{bill.pk}/"
        submitted = self.client.post(base + "submit/", {}, format="json")
        self.assertEqual(submitted.status_code, 200, submitted.data)
        denied = self.client.post(base + "approve/", {}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.approver)
        approved = self.client.post(base + "approve/", {}, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], SupplierBill.Status.APPROVED)

    def test_supplier_bill_api_cannot_access_another_school_bill(self):
        from expenses.models import Supplier, SupplierBill
        other = School.objects.create(name="Other Bills School", code="other-bills-school")
        other_period = FinancialPeriod.objects.create(
            school=other, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        other_expense = Account.objects.create(
            school=other, code="5100", name="Other Repairs", category="EXPENSE"
        )
        other_payable = Account.objects.create(
            school=other, code="2000", name="Other Payables", category="LIABILITY"
        )
        other_category = ExpenseCategory.objects.create(
            school=other, code="REPAIRS", name="Repairs", expense_account=other_expense
        )
        other_supplier = Supplier.objects.create(school=other, name="Other Supplier")
        other_bill = SupplierBill.objects.create(
            school=other, supplier=other_supplier, category=other_category,
            period=other_period, payable_account=other_payable,
            bill_number="BILL-000001", supplier_invoice_number="OTHER-INV-001",
            bill_date="2026-04-01", due_date="2026-04-30",
            description="Other school purchase", amount="1000.00", created_by=self.creator,
        )
        self.client.force_authenticate(self.creator)
        response = self.client.get(
            f"/api/schools/{self.school.pk}/expenses/bills/{other_bill.pk}/"
        )
        self.assertEqual(response.status_code, 404)



class ExpenseBudgetTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="budget-owner", password="test-password")
        self.school = School.objects.create(name="Budget School", code="budget-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
        self.period = FinancialPeriod.objects.create(school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31")
        self.expense_account = Account.objects.create(school=self.school, code="5200", name="Repairs", category="EXPENSE")
        self.category = ExpenseCategory.objects.create(school=self.school, code="REPAIRS", name="Repairs", expense_account=self.expense_account)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_budget_api_returns_budget_actual_and_variance(self):
        from expenses.models import ExpenseBudget, Supplier, SupplierBill
        budget = self.client.post(
            f"/api/schools/{self.school.pk}/expenses/budgets/",
            {"period": self.period.pk, "category": self.category.pk, "budget_amount": "100000.00", "notes": "Term repairs"},
            format="json",
        )
        self.assertEqual(budget.status_code, 201, budget.data)
        Expense.objects.create(
            school=self.school, category=self.category, period=self.period,
            expense_number="EXP-000001", expense_date="2026-02-01",
            description="Minor repair", amount="15000.00", payment_method="CASH",
            status=Expense.Status.POSTED,
        )
        supplier = Supplier.objects.create(school=self.school, name="Budget supplier")
        payable = Account.objects.create(school=self.school, code="2000", name="Trade Payables", category="LIABILITY")
        SupplierBill.objects.create(
            school=self.school, supplier=supplier, category=self.category,
            period=self.period, payable_account=payable, bill_number="BILL-000001",
            supplier_invoice_number="SUP-001", bill_date="2026-02-02", due_date="2026-02-28",
            description="Repair parts", amount="25000.00", status=SupplierBill.Status.POSTED,
            created_by=self.user,
        )
        response = self.client.get(f"/api/schools/{self.school.pk}/expenses/budgets/?period={self.period.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["actual_amount"], "40000.00")
        self.assertEqual(response.data[0]["variance"], "60000.00")
        self.assertEqual(response.data[0]["utilisation_percent"], 40.0)

    def test_budget_cannot_reference_another_school_category(self):
        other = School.objects.create(name="Other Budget School", code="other-budget-school")
        other_account = Account.objects.create(school=other, code="5200", name="Other Repairs", category="EXPENSE")
        other_category = ExpenseCategory.objects.create(school=other, code="REPAIRS", name="Repairs", expense_account=other_account)
        response = self.client.post(
            f"/api/schools/{self.school.pk}/expenses/budgets/",
            {"period": self.period.pk, "category": other_category.pk, "budget_amount": "1000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class PurchaseOrderApprovalTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from expenses.models import Supplier
        self.User = get_user_model()
        self.creator = self.User.objects.create_user(username="po-creator", password="test-password")
        self.admin = self.User.objects.create_user(username="po-admin", password="test-password")
        self.owner = self.User.objects.create_user(username="po-owner", password="test-password")
        self.school = School.objects.create(name="Procurement School", code="procurement-school")
        SchoolMembership.objects.create(school=self.school, user=self.creator, role="ACCOUNTANT")
        SchoolMembership.objects.create(school=self.school, user=self.admin, role="ADMIN")
        SchoolMembership.objects.create(school=self.school, user=self.owner, role="OWNER")
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY26", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        self.supplier = Supplier.objects.create(school=self.school, name="Learning Supplies Ltd")
        self.client = APIClient()
        self.client.force_authenticate(self.creator)

    def test_purchase_order_requires_sequential_configured_approvals(self):
        from expenses.models import PurchaseOrder, PurchaseOrderApproval, ProcurementApprovalRule
        base = f"/api/schools/{self.school.pk}/expenses/"
        ProcurementApprovalRule.objects.create(
            school=self.school, min_amount="0.00", step_number=1, approver_role="ADMIN"
        )
        ProcurementApprovalRule.objects.create(
            school=self.school, min_amount="10000.00", step_number=2, approver_role="OWNER"
        )
        created = self.client.post(base + "purchase-orders/", {
            "supplier": self.supplier.pk, "period": self.period.pk,
            "order_date": "2026-05-01", "expected_date": "2026-05-15",
            "description": "Term 2 learning materials",
            "lines": [
                {"description": "Exercise books", "quantity": "100.000", "unit_cost": "150.00"},
                {"description": "Pens", "quantity": "50.000", "unit_cost": "50.00"},
            ],
        }, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["total_amount"], "17500.00")
        order_id = created.data["id"]
        submitted = self.client.post(f"{base}purchase-orders/{order_id}/submit/", {}, format="json")
        self.assertEqual(submitted.status_code, 200, submitted.data)
        self.assertEqual(submitted.data["status"], PurchaseOrder.Status.SUBMITTED)
        self.assertEqual(PurchaseOrderApproval.objects.filter(purchase_order_id=order_id).count(), 2)

        # Creator cannot approve their own order, and only the configured role can act.
        denied = self.client.post(f"{base}purchase-orders/{order_id}/approve/", {}, format="json")
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.admin)
        first = self.client.post(f"{base}purchase-orders/{order_id}/approve/", {}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["status"], PurchaseOrder.Status.SUBMITTED)

        self.client.force_authenticate(self.owner)
        final = self.client.post(f"{base}purchase-orders/{order_id}/approve/", {}, format="json")
        self.assertEqual(final.status_code, 200, final.data)
        self.assertEqual(final.data["status"], PurchaseOrder.Status.APPROVED)

    def test_purchase_order_rejects_cross_school_supplier(self):
        from expenses.models import Supplier
        other = School.objects.create(name="Other School", code="other-procurement")
        foreign_supplier = Supplier.objects.create(school=other, name="Foreign supplier")
        response = self.client.post(f"/api/schools/{self.school.pk}/expenses/purchase-orders/", {
            "supplier": foreign_supplier.pk, "period": self.period.pk,
            "order_date": "2026-05-01", "description": "Invalid order",
            "lines": [{"description": "Item", "quantity": "1", "unit_cost": "100.00"}],
        }, format="json")
        self.assertEqual(response.status_code, 400)
