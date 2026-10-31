from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from accounts.models import School
from ledger.models import Account, FinancialPeriod, JournalEntry


class Employee(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="employees")
    employee_number = models.CharField(max_length=40)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    job_title = models.CharField(max_length=120, blank=True)
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2)
    regular_cash_allowances = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    monthly_other_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    is_resident = models.BooleanField(default=True)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "employee_number"], name="unique_employee_number_school"),
            models.CheckConstraint(condition=Q(basic_salary__gte=0) & Q(regular_cash_allowances__gte=0) & Q(monthly_other_deductions__gte=0), name="employee_pay_components_nonnegative"),
        ]

    def clean(self):
        super().clean()
        if self.basic_salary < 0:
            raise ValidationError({"basic_salary": "Basic salary cannot be negative."})
        if self.regular_cash_allowances < 0:
            raise ValidationError({"regular_cash_allowances": "Regular allowances cannot be negative."})
        if self.monthly_other_deductions < 0:
            raise ValidationError({"monthly_other_deductions": "Other deductions cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class PayrollRule(models.Model):
    class Code(models.TextChoices):
        NSSF = "NSSF", "NSSF"
        SHIF = "SHIF", "SHIF"
        HOUSING_LEVY = "HOUSING_LEVY", "Affordable Housing Levy"
        PERSONAL_RELIEF = "PERSONAL_RELIEF", "Personal tax relief"
        NITA_LEVY = "NITA_LEVY", "NITA industrial training levy"

    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name="payroll_rules")
    code = models.CharField(max_length=24, choices=Code.choices)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    employee_rate = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("0.000000"))
    employer_rate = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("0.000000"))
    ceiling = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    minimum_employee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    fixed_employee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    fixed_employer = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    deductible_for_paye = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code", "-effective_from"]
        constraints = [
            models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gte=models.F("effective_from")), name="payroll_rule_effective_range"),
            models.CheckConstraint(condition=Q(employee_rate__gte=0) & Q(employer_rate__gte=0), name="payroll_rule_rates_nonnegative"),
            models.UniqueConstraint(fields=["school", "code", "effective_from"], condition=Q(school__isnull=False), name="unique_school_payroll_rule_effective"),
            models.UniqueConstraint(fields=["code", "effective_from"], condition=Q(school__isnull=True), name="unique_global_payroll_rule_effective"),
        ]

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "End date cannot precede effective date."})


class PayrollTaxBand(models.Model):
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name="payroll_tax_bands")
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    lower_bound = models.DecimalField(max_digits=14, decimal_places=2)
    upper_bound = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=8, decimal_places=6)

    class Meta:
        ordering = ["lower_bound"]
        constraints = [
            models.CheckConstraint(condition=Q(lower_bound__gte=0), name="payroll_tax_band_lower_nonnegative"),
            models.CheckConstraint(condition=Q(upper_bound__isnull=True) | Q(upper_bound__gt=models.F("lower_bound")), name="payroll_tax_band_upper_after_lower"),
            models.CheckConstraint(condition=Q(rate__gte=0) & Q(rate__lte=1), name="payroll_tax_band_rate_range"),
            models.UniqueConstraint(fields=["school", "effective_from", "lower_bound"], condition=Q(school__isnull=False), name="unique_school_tax_band"),
            models.UniqueConstraint(fields=["effective_from", "lower_bound"], condition=Q(school__isnull=True), name="unique_global_tax_band"),
        ]


class PayrollSettings(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="payroll_settings")
    salary_expense_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_salary_settings")
    net_payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_net_payable_settings")
    paye_payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_paye_settings")
    nssf_payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_nssf_settings")
    shif_payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_shif_settings")
    housing_levy_payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_housing_settings")
    other_deductions_payable_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="payroll_other_deductions_settings")
    nita_payable_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.PROTECT, related_name="payroll_nita_settings")

    def clean(self):
        super().clean()
        expected = [
            (self.salary_expense_account, Account.Category.EXPENSE, "salary_expense_account"),
            (self.net_payable_account, Account.Category.LIABILITY, "net_payable_account"),
            (self.paye_payable_account, Account.Category.LIABILITY, "paye_payable_account"),
            (self.nssf_payable_account, Account.Category.LIABILITY, "nssf_payable_account"),
            (self.shif_payable_account, Account.Category.LIABILITY, "shif_payable_account"),
            (self.housing_levy_payable_account, Account.Category.LIABILITY, "housing_levy_payable_account"),
            (self.nita_payable_account, Account.Category.LIABILITY, "nita_payable_account"),
            (self.other_deductions_payable_account, Account.Category.LIABILITY, "other_deductions_payable_account"),
        ]
        errors = {}
        for account, category, field in expected:
            if account and (account.school_id != self.school_id or account.category != category):
                errors[field] = f"Select a {category.lower()} account belonging to this school."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PayrollRun(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="payroll_runs")
    period = models.ForeignKey(FinancialPeriod, on_delete=models.PROTECT, related_name="payroll_runs")
    payroll_month = models.DateField()
    pay_date = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="source_payroll_run")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payroll_month"]
        constraints = [models.UniqueConstraint(fields=["school", "payroll_month"], name="unique_payroll_month_school")]

    def clean(self):
        super().clean()
        errors = {}
        if self.period_id and self.period.school_id != self.school_id:
            errors["period"] = "Financial period must belong to this school."
        if self.payroll_month and self.payroll_month.day != 1:
            errors["payroll_month"] = "Payroll month must use the first day of the month."
        if self.period_id and self.payroll_month:
            payroll_month = self._meta.get_field("payroll_month").to_python(self.payroll_month)
            period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
            period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
            if not (period_start <= payroll_month <= period_end):
                errors["payroll_month"] = "Payroll month must fall within the selected financial period."
        if self.period_id and self.pay_date:
            pay_date = self._meta.get_field("pay_date").to_python(self.pay_date)
            period_start = FinancialPeriod._meta.get_field("starts_on").to_python(self.period.starts_on)
            period_end = FinancialPeriod._meta.get_field("ends_on").to_python(self.period.ends_on)
            if not (period_start <= pay_date <= period_end):
                errors["pay_date"] = "Pay date must fall within the selected financial period."
        if errors:
            raise ValidationError(errors)

    @property
    def gross_total(self):
        return sum((line.gross_pay for line in self.lines.all()), Decimal("0.00"))

    @property
    def net_total(self):
        return sum((line.net_pay for line in self.lines.all()), Decimal("0.00"))

    @property
    def employer_contributions_total(self):
        return sum((line.nssf_employer + line.housing_levy_employer + line.nita_levy_employer for line in self.lines.all()), Decimal("0.00"))

    def save(self, *args, **kwargs):
        if self.pk and PayrollRun.objects.filter(pk=self.pk, status=self.Status.POSTED).exists():
            raise ValidationError("Posted payroll runs are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)


class PayrollLine(models.Model):
    run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payroll_lines")
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2)
    other_earnings = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    gross_pay = models.DecimalField(max_digits=14, decimal_places=2)
    taxable_pay = models.DecimalField(max_digits=14, decimal_places=2)
    paye = models.DecimalField(max_digits=14, decimal_places=2)
    nssf_employee = models.DecimalField(max_digits=14, decimal_places=2)
    shif_employee = models.DecimalField(max_digits=14, decimal_places=2)
    housing_levy_employee = models.DecimalField(max_digits=14, decimal_places=2)
    other_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_pay = models.DecimalField(max_digits=14, decimal_places=2)
    nssf_employer = models.DecimalField(max_digits=14, decimal_places=2)
    housing_levy_employer = models.DecimalField(max_digits=14, decimal_places=2)
    nita_levy_employer = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "employee"], name="unique_employee_per_payroll_run"),
            models.CheckConstraint(condition=Q(gross_pay__gte=0) & Q(net_pay__gte=0), name="payroll_line_pay_nonnegative"),
        ]

    def save(self, *args, **kwargs):
        if self.run.status != PayrollRun.Status.DRAFT:
            raise ValidationError("Lines on posted payroll runs are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.run.status != PayrollRun.Status.DRAFT:
            raise ValidationError("Lines on posted payroll runs are immutable.")
        return super().delete(*args, **kwargs)
