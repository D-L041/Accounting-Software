import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from decimal import Decimal
from datetime import date


def seed_kenyan_rules(apps, schema_editor):
    PayrollRule = apps.get_model("payroll", "PayrollRule")
    PayrollTaxBand = apps.get_model("payroll", "PayrollTaxBand")
    rules = [
        ("NSSF", date(2026, 2, 1), None, Decimal("0.06"), Decimal("0.06"), Decimal("108000.00"), Decimal("0.00"), Decimal("0.00"), False),
        ("NSSF", date(2026, 1, 1), date(2026, 1, 31), Decimal("0.06"), Decimal("0.06"), Decimal("72000.00"), Decimal("0.00"), Decimal("0.00"), False),
        ("SHIF", date(2024, 10, 1), None, Decimal("0.0275"), Decimal("0.00"), None, Decimal("300.00"), Decimal("0.00"), True),
        ("HOUSING_LEVY", date(2024, 3, 19), None, Decimal("0.015"), Decimal("0.015"), None, Decimal("0.00"), Decimal("0.00"), True),
        ("PERSONAL_RELIEF", date(2023, 7, 1), None, Decimal("0.00"), Decimal("0.00"), None, Decimal("0.00"), Decimal("2400.00"), False),
    ]
    for code, start, end, erate, orate, ceiling, minimum, fixed, deductible in rules:
        PayrollRule.objects.create(
            school=None, code=code, effective_from=start, effective_to=end,
            employee_rate=erate, employer_rate=orate, ceiling=ceiling,
            minimum_employee=minimum, fixed_employee=fixed,
            deductible_for_paye=deductible,
        )
    bands = [
        (Decimal("0.00"), Decimal("24000.00"), Decimal("0.10")),
        (Decimal("24000.00"), Decimal("32333.00"), Decimal("0.25")),
        (Decimal("32333.00"), Decimal("500000.00"), Decimal("0.30")),
        (Decimal("500000.00"), Decimal("800000.00"), Decimal("0.325")),
        (Decimal("800000.00"), None, Decimal("0.35")),
    ]
    for lower, upper, rate in bands:
        PayrollTaxBand.objects.create(
            school=None, effective_from=date(2023, 7, 1), lower_bound=lower,
            upper_bound=upper, rate=rate,
        )


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("ledger", "0004_bank_reconciliation"),
    ]

    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_number", models.CharField(max_length=40)),
                ("first_name", models.CharField(max_length=80)),
                ("last_name", models.CharField(max_length=80)),
                ("job_title", models.CharField(blank=True, max_length=120)),
                ("basic_salary", models.DecimalField(decimal_places=2, max_digits=14)),
                ("is_resident", models.BooleanField(default=True)),
                ("hire_date", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employees", to="accounts.school")),
            ],
            options={"ordering": ["last_name", "first_name"]},
        ),
        migrations.AddConstraint(model_name="employee", constraint=models.UniqueConstraint(fields=("school", "employee_number"), name="unique_employee_number_school")),
        migrations.AddConstraint(model_name="employee", constraint=models.CheckConstraint(condition=Q(basic_salary__gte=0), name="employee_basic_salary_nonnegative")),
        migrations.CreateModel(
            name="PayrollRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(choices=[("NSSF", "NSSF"), ("SHIF", "SHIF"), ("HOUSING_LEVY", "Affordable Housing Levy"), ("PERSONAL_RELIEF", "Personal tax relief")], max_length=24)),
                ("effective_from", models.DateField()),
                ("effective_to", models.DateField(blank=True, null=True)),
                ("employee_rate", models.DecimalField(decimal_places=6, default=Decimal("0.000000"), max_digits=8)),
                ("employer_rate", models.DecimalField(decimal_places=6, default=Decimal("0.000000"), max_digits=8)),
                ("ceiling", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("minimum_employee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("fixed_employee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("deductible_for_paye", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("school", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="payroll_rules", to="accounts.school")),
            ],
            options={"ordering": ["code", "-effective_from"]},
        ),
        migrations.AddConstraint(model_name="payrollrule", constraint=models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gte=models.F("effective_from")), name="payroll_rule_effective_range")),
        migrations.AddConstraint(model_name="payrollrule", constraint=models.CheckConstraint(condition=Q(employee_rate__gte=0) & Q(employer_rate__gte=0), name="payroll_rule_rates_nonnegative")),
        migrations.AddConstraint(model_name="payrollrule", constraint=models.UniqueConstraint(fields=("school", "code", "effective_from"), condition=Q(school__isnull=False), name="unique_school_payroll_rule_effective")),
        migrations.AddConstraint(model_name="payrollrule", constraint=models.UniqueConstraint(fields=("code", "effective_from"), condition=Q(school__isnull=True), name="unique_global_payroll_rule_effective")),
        migrations.CreateModel(
            name="PayrollTaxBand",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_from", models.DateField()),
                ("effective_to", models.DateField(blank=True, null=True)),
                ("lower_bound", models.DecimalField(decimal_places=2, max_digits=14)),
                ("upper_bound", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("rate", models.DecimalField(decimal_places=6, max_digits=8)),
                ("school", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="payroll_tax_bands", to="accounts.school")),
            ],
            options={"ordering": ["lower_bound"]},
        ),
        migrations.AddConstraint(model_name="payrolltaxband", constraint=models.CheckConstraint(condition=Q(lower_bound__gte=0), name="payroll_tax_band_lower_nonnegative")),
        migrations.AddConstraint(model_name="payrolltaxband", constraint=models.CheckConstraint(condition=Q(upper_bound__isnull=True) | Q(upper_bound__gt=models.F("lower_bound")), name="payroll_tax_band_upper_after_lower")),
        migrations.AddConstraint(model_name="payrolltaxband", constraint=models.CheckConstraint(condition=Q(rate__gte=0) & Q(rate__lte=1), name="payroll_tax_band_rate_range")),
        migrations.AddConstraint(model_name="payrolltaxband", constraint=models.UniqueConstraint(fields=("school", "effective_from", "lower_bound"), condition=Q(school__isnull=False), name="unique_school_tax_band")),
        migrations.AddConstraint(model_name="payrolltaxband", constraint=models.UniqueConstraint(fields=("effective_from", "lower_bound"), condition=Q(school__isnull=True), name="unique_global_tax_band")),
        migrations.CreateModel(
            name="PayrollSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("housing_levy_payable_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_housing_settings", to="ledger.account")),
                ("net_payable_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_net_payable_settings", to="ledger.account")),
                ("nssf_payable_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_nssf_settings", to="ledger.account")),
                ("paye_payable_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_paye_settings", to="ledger.account")),
                ("salary_expense_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_salary_settings", to="ledger.account")),
                ("shif_payable_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_shif_settings", to="ledger.account")),
                ("school", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payroll_settings", to="accounts.school")),
            ],
        ),
        migrations.CreateModel(
            name="PayrollRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payroll_month", models.DateField()),
                ("pay_date", models.DateField()),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted")], default="DRAFT", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_payroll_run", to="ledger.journalentry")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_runs", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payroll_runs", to="accounts.school")),
            ],
            options={"ordering": ["-payroll_month"]},
        ),
        migrations.AddConstraint(model_name="payrollrun", constraint=models.UniqueConstraint(fields=("school", "payroll_month"), name="unique_payroll_month_school")),
        migrations.CreateModel(
            name="PayrollLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("basic_salary", models.DecimalField(decimal_places=2, max_digits=14)),
                ("other_earnings", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("gross_pay", models.DecimalField(decimal_places=2, max_digits=14)),
                ("taxable_pay", models.DecimalField(decimal_places=2, max_digits=14)),
                ("paye", models.DecimalField(decimal_places=2, max_digits=14)),
                ("nssf_employee", models.DecimalField(decimal_places=2, max_digits=14)),
                ("shif_employee", models.DecimalField(decimal_places=2, max_digits=14)),
                ("housing_levy_employee", models.DecimalField(decimal_places=2, max_digits=14)),
                ("other_deductions", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("net_pay", models.DecimalField(decimal_places=2, max_digits=14)),
                ("nssf_employer", models.DecimalField(decimal_places=2, max_digits=14)),
                ("housing_levy_employer", models.DecimalField(decimal_places=2, max_digits=14)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_lines", to="payroll.employee")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="payroll.payrollrun")),
            ],
        ),
        migrations.AddConstraint(model_name="payrollline", constraint=models.UniqueConstraint(fields=("run", "employee"), name="unique_employee_per_payroll_run")),
        migrations.AddConstraint(model_name="payrollline", constraint=models.CheckConstraint(condition=Q(gross_pay__gte=0) & Q(net_pay__gte=0), name="payroll_line_pay_nonnegative")),
        migrations.RunPython(seed_kenyan_rules, migrations.RunPython.noop),
    ]
