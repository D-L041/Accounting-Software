from datetime import date
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


def seed_nita_levy(apps, schema_editor):
    PayrollRule = apps.get_model("payroll", "PayrollRule")
    PayrollRule.objects.get_or_create(
        school=None,
        code="NITA_LEVY",
        effective_from=date(2007, 7, 1),
        defaults={
            "effective_to": None,
            "employee_rate": Decimal("0.000000"),
            "employer_rate": Decimal("0.000000"),
            "ceiling": None,
            "minimum_employee": Decimal("0.00"),
            "fixed_employee": Decimal("0.00"),
            "fixed_employer": Decimal("50.00"),
            "deductible_for_paye": False,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0002_nssf_paye_deduction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payrollrule",
            name="code",
            field=models.CharField(
                choices=[
                    ("NSSF", "NSSF"), ("SHIF", "SHIF"),
                    ("HOUSING_LEVY", "Affordable Housing Levy"),
                    ("PERSONAL_RELIEF", "Personal tax relief"),
                    ("NITA_LEVY", "NITA industrial training levy"),
                ],
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="payrollrule",
            name="fixed_employer",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddConstraint(
            model_name="payrollrule",
            constraint=models.CheckConstraint(condition=models.Q(("fixed_employer__gte", 0)), name="payroll_fixed_employer_nonnegative"),
        ),
        migrations.AddField(
            model_name="payrollsettings",
            name="nita_payable_account",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payroll_nita_settings", to="ledger.account"),
        ),
        migrations.AddField(
            model_name="payrollline",
            name="nita_levy_employer",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.RunPython(seed_nita_levy, migrations.RunPython.noop),
    ]
