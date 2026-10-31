import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0003_nita_employer_levy"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee", name="monthly_insurance_premiums",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="employee", name="monthly_mortgage_interest",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="employee", name="monthly_post_retirement_medical",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="employee", name="monthly_additional_pension",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="employee", name="tax_claims_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="employee", name="tax_claims_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="employee", name="tax_exemption_certificate_ref",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="employee", name="tax_exemption_valid_from",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employee", name="tax_exemption_valid_to",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employee", name="tax_exemption_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveConstraint(
            model_name="employee", name="employee_pay_components_nonnegative",
        ),
        migrations.AddConstraint(
            model_name="employee",
            constraint=models.CheckConstraint(
                condition=Q(basic_salary__gte=0)
                & Q(regular_cash_allowances__gte=0)
                & Q(monthly_other_deductions__gte=0)
                & Q(monthly_insurance_premiums__gte=0)
                & Q(monthly_mortgage_interest__gte=0)
                & Q(monthly_post_retirement_medical__gte=0)
                & Q(monthly_additional_pension__gte=0),
                name="employee_pay_components_nonnegative",
            ),
        ),
        migrations.AddField(
            model_name="payrollline", name="insurance_premium_claimed",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollline", name="insurance_relief",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollline", name="mortgage_interest_deduction",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollline", name="post_retirement_medical_deduction",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollline", name="additional_pension_employee",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollline", name="additional_pension_allowable",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollline", name="tax_exempt_income",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14),
        ),
    ]
