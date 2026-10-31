from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from ledger.models import Account, FinancialPeriod, JournalEntry
from payroll.models import Employee, PayrollLine, PayrollRun, PayrollSettings


class PayrollWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="payroll-owner", password="test-password")
        self.school = School.objects.create(name="Payroll School", code="payroll-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role="OWNER")
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY2026", starts_on="2026-01-01", ends_on="2026-12-31"
        )
        self.salary_expense = Account.objects.create(
            school=self.school, code="6000", name="Salaries Expense", category="EXPENSE"
        )
        self.net_payable = Account.objects.create(
            school=self.school, code="2100", name="Net Salaries Payable", category="LIABILITY"
        )
        self.paye = Account.objects.create(
            school=self.school, code="2110", name="PAYE Payable", category="LIABILITY"
        )
        self.nssf = Account.objects.create(
            school=self.school, code="2120", name="NSSF Payable", category="LIABILITY"
        )
        self.shif = Account.objects.create(
            school=self.school, code="2130", name="SHIF Payable", category="LIABILITY"
        )
        self.housing = Account.objects.create(
            school=self.school, code="2140", name="Housing Levy Payable", category="LIABILITY"
        )
        self.other_deductions = Account.objects.create(
            school=self.school, code="2150", name="Other Deductions Payable", category="LIABILITY"
        )
        self.nita = Account.objects.create(
            school=self.school, code="2160", name="NITA Levy Payable", category="LIABILITY"
        )
        self.employee = Employee.objects.create(
            school=self.school, employee_number="STF001", first_name="Jane",
            last_name="Teacher", job_title="Teacher", basic_salary="50000.00",
            hire_date="2025-01-01",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def configure_payroll(self):
        return self.client.post(
            f"/api/schools/{self.school.pk}/payroll/settings/",
            {
                "salary_expense_account": self.salary_expense.pk,
                "net_payable_account": self.net_payable.pk,
                "paye_payable_account": self.paye.pk,
                "nssf_payable_account": self.nssf.pk,
                "shif_payable_account": self.shif.pk,
                "housing_levy_payable_account": self.housing.pk,
                "other_deductions_payable_account": self.other_deductions.pk,
                "nita_payable_account": self.nita.pk,
            }, format="json",
        )

    def test_february_2026_payroll_uses_effective_statutory_rules(self):
        response = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-02-01", "pay_date": "2026-02-28"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        line = PayrollLine.objects.get(run_id=response.data["id"], employee=self.employee)
        self.assertEqual(line.nssf_employee, Decimal("3000.00"))
        self.assertEqual(line.nssf_employer, Decimal("3000.00"))
        self.assertEqual(line.shif_employee, Decimal("1375.00"))
        self.assertEqual(line.housing_levy_employee, Decimal("750.00"))
        self.assertEqual(line.housing_levy_employer, Decimal("750.00"))
        self.assertEqual(line.nita_levy_employer, Decimal("50.00"))
        self.assertEqual(response.data["employer_contributions_total"], "3800.00")
        self.assertEqual(line.taxable_pay, Decimal("44875.00"))
        self.assertEqual(line.paye, Decimal("5845.85"))
        self.assertEqual(line.net_pay, Decimal("39029.15"))

    def test_2026_payroll_matches_independent_100k_statutory_benchmark(self):
        Employee.objects.filter(pk=self.employee.pk).update(basic_salary=Decimal("100000.00"))
        response = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-02-01", "pay_date": "2026-02-28"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        line = PayrollLine.objects.get(run_id=response.data["id"], employee=self.employee)
        self.assertEqual(line.nssf_employee, Decimal("6000.00"))
        self.assertEqual(line.shif_employee, Decimal("2750.00"))
        self.assertEqual(line.housing_levy_employee, Decimal("1500.00"))
        self.assertEqual(line.nita_levy_employer, Decimal("50.00"))
        self.assertEqual(line.taxable_pay, Decimal("89750.00"))
        self.assertEqual(line.paye, Decimal("19308.35"))
        self.assertEqual(line.net_pay, Decimal("70441.65"))

    def test_january_2026_nssf_uses_previous_effective_ceiling(self):
        Employee.objects.filter(pk=self.employee.pk).update(basic_salary=Decimal("100000.00"))
        response = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-01-01", "pay_date": "2026-01-30"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        line = PayrollLine.objects.get(run_id=response.data["id"])
        self.assertEqual(line.nssf_employee, Decimal("4320.00"))
        self.assertEqual(line.nssf_employer, Decimal("4320.00"))

    def test_posting_payroll_creates_balanced_ledger_journal(self):
        created = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-02-01", "pay_date": "2026-02-28"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        configured = self.configure_payroll()
        self.assertEqual(configured.status_code, 201, configured.data)
        posted = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/{created.data['id']}/post/",
            {}, format="json",
        )
        self.assertEqual(posted.status_code, 200, posted.data)
        self.assertEqual(posted.data["status"], PayrollRun.Status.POSTED)
        journal = JournalEntry.objects.get(pk=posted.data["journal_entry"])
        self.assertTrue(journal.posted)
        self.assertEqual(
            sum(line.debit for line in journal.lines.all()),
            sum(line.credit for line in journal.lines.all()),
        )
        self.assertEqual(journal.lines.get(debit__gt=0).account_id, self.salary_expense.pk)

    def test_payroll_settings_reject_cross_school_or_wrong_category_accounts(self):
        other = School.objects.create(name="Other Payroll School", code="other-payroll-school")
        other_account = Account.objects.create(
            school=other, code="6000", name="Other Salary Expense", category="EXPENSE"
        )
        response = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/settings/",
            {
                "salary_expense_account": other_account.pk,
                "net_payable_account": self.net_payable.pk,
                "paye_payable_account": self.paye.pk,
                "nssf_payable_account": self.nssf.pk,
                "shif_payable_account": self.shif.pk,
                "housing_levy_payable_account": self.housing.pk,
                "other_deductions_payable_account": self.other_deductions.pk,
            }, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PayrollSettings.objects.filter(school=self.school).count(), 0)

    def test_viewer_cannot_create_employee(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role="VIEWER")
        response = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/employees/",
            {
                "employee_number": "STF002", "first_name": "Read", "last_name": "Only",
                "basic_salary": "20000.00", "hire_date": "2026-01-01",
            }, format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_employee_list_is_limited_to_the_selected_school(self):
        other = School.objects.create(name="Other Payroll Tenant", code="other-payroll-tenant")
        Employee.objects.create(
            school=other, employee_number="OTHER001", first_name="Other",
            last_name="Staff", basic_salary="30000.00", hire_date="2025-01-01",
        )
        response = self.client.get(f"/api/schools/{self.school.pk}/payroll/employees/")
        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data}
        self.assertEqual(returned_ids, {self.employee.pk})

    def test_other_employee_deductions_are_credited_to_their_liability_account(self):
        Employee.objects.filter(pk=self.employee.pk).update(monthly_other_deductions=Decimal("1000.00"))
        created = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-02-01", "pay_date": "2026-02-28"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["lines"][0]["other_deductions"], "1000.00")
        self.assertEqual(self.configure_payroll().status_code, 201)
        posted = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/{created.data['id']}/post/",
            {}, format="json",
        )
        self.assertEqual(posted.status_code, 200, posted.data)
        journal = JournalEntry.objects.get(pk=posted.data["journal_entry"])
        self.assertEqual(journal.lines.get(account=self.other_deductions).credit, Decimal("1000.00"))
        self.assertEqual(journal.lines.get(account=self.nita).credit, Decimal("50.00"))
        self.assertEqual(
            sum(line.debit for line in journal.lines.all()),
            sum(line.credit for line in journal.lines.all()),
        )



    def test_statutory_exports_require_posted_payroll_and_are_audited(self):
        from auditlog.models import AuditEvent

        created = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-02-01", "pay_date": "2026-02-28"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        base = f"/api/schools/{self.school.pk}/payroll/runs/{created.data['id']}/statutory-export/"
        draft_schedule = self.client.get(base + "?schedule=NSSF")
        self.assertEqual(draft_schedule.status_code, 400)
        register = self.client.get(base + "?schedule=REGISTER")
        self.assertEqual(register.status_code, 200)
        self.assertIn("Employee number", register.content.decode("utf-8"))
        self.assertEqual(self.configure_payroll().status_code, 201)
        posted = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/{created.data['id']}/post/",
            {}, format="json",
        )
        self.assertEqual(posted.status_code, 200, posted.data)
        nssf = self.client.get(base + "?schedule=NSSF")
        self.assertEqual(nssf.status_code, 200)
        self.assertIn("3000.00,3000.00,6000.00", nssf.content.decode("utf-8"))
        self.assertTrue(AuditEvent.objects.filter(
            school=self.school, action="PAYROLL_EXPORT_DOWNLOADED",
            entity_id=str(created.data["id"]),
        ).exists())

    def test_statutory_export_rejects_unknown_schedule(self):
        created = self.client.post(
            f"/api/schools/{self.school.pk}/payroll/runs/",
            {"period": self.period.pk, "payroll_month": "2026-02-01", "pay_date": "2026-02-28"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        response = self.client.get(
            f"/api/schools/{self.school.pk}/payroll/runs/{created.data['id']}/statutory-export/?schedule=INVALID"
        )
        self.assertEqual(response.status_code, 400)
