from django.db import migrations


def mark_nssf_as_paye_deductible(apps, schema_editor):
    PayrollRule = apps.get_model("payroll", "PayrollRule")
    PayrollRule.objects.filter(code="NSSF").update(deductible_for_paye=True)


def reverse_nssf_paye_deduction(apps, schema_editor):
    PayrollRule = apps.get_model("payroll", "PayrollRule")
    PayrollRule.objects.filter(code="NSSF").update(deductible_for_paye=False)


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            mark_nssf_as_paye_deductible,
            reverse_nssf_paye_deduction,
        ),
    ]
