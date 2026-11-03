import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def assign_existing_ledger_rows(apps, schema_editor):
    School = apps.get_model("accounts", "School")
    FinancialPeriod = apps.get_model("ledger", "FinancialPeriod")
    Account = apps.get_model("ledger", "Account")
    JournalEntry = apps.get_model("ledger", "JournalEntry")

    if not (FinancialPeriod.objects.exists() or Account.objects.exists() or JournalEntry.objects.exists()):
        return

    legacy_school, _ = School.objects.get_or_create(
        code="legacy-ledger-import",
        defaults={
            "name": "Legacy Ledger Import — assign an owner before use",
            "currency": "KES",
            "timezone": "Africa/Nairobi",
        },
    )
    FinancialPeriod.objects.filter(school__isnull=True).update(school=legacy_school)
    Account.objects.filter(school__isnull=True).update(school=legacy_school)
    JournalEntry.objects.filter(school__isnull=True).update(school=legacy_school)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("ledger", "0002_journal_line_exactly_one_side"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialperiod",
            name="school",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="financial_periods", to="accounts.school"),
        ),
        migrations.AddField(
            model_name="account",
            name="school",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chart_of_accounts", to="accounts.school"),
        ),
        migrations.AddField(
            model_name="journalentry",
            name="school",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="journal_entries", to="accounts.school"),
        ),
        migrations.RunPython(assign_existing_ledger_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="financialperiod",
            name="school",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_periods", to="accounts.school"),
        ),
        migrations.AlterField(
            model_name="account",
            name="school",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chart_of_accounts", to="accounts.school"),
        ),
        migrations.AlterField(
            model_name="journalentry",
            name="school",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="journal_entries", to="accounts.school"),
        ),
        migrations.AlterField(
            model_name="financialperiod",
            name="name",
            field=models.CharField(max_length=80),
        ),
        migrations.AlterField(
            model_name="account",
            name="code",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name="journalentry",
            name="reference",
            field=models.CharField(max_length=40),
        ),
        migrations.AddConstraint(
            model_name="financialperiod",
            constraint=models.UniqueConstraint(fields=("school", "name"), name="unique_financial_period_per_school"),
        ),
        migrations.AddConstraint(
            model_name="financialperiod",
            constraint=models.CheckConstraint(condition=Q(ends_on__gte=models.F("starts_on")), name="financial_period_end_after_start"),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(fields=("school", "code"), name="unique_account_code_per_school"),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(fields=("school", "reference"), name="unique_journal_reference_per_school"),
        ),
    ]
