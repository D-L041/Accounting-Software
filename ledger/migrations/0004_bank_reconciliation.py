import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ledger", "0003_school_scope_ledger"),
    ]

    operations = [
        migrations.CreateModel(
            name="BankStatement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("statement_start", models.DateField()),
                ("statement_end", models.DateField()),
                ("opening_balance", models.DecimalField(decimal_places=2, max_digits=14)),
                ("closing_balance", models.DecimalField(decimal_places=2, max_digits=14)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("RECONCILED", "Reconciled")], default="DRAFT", max_length=12)),
                ("reconciled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bank_statements", to="ledger.account")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bank_statements", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_statements", to="accounts.school")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-statement_end", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="bankstatement",
            constraint=models.UniqueConstraint(fields=("school", "account", "statement_end"), name="unique_bank_statement_end_per_account"),
        ),
        migrations.AddConstraint(
            model_name="bankstatement",
            constraint=models.CheckConstraint(condition=Q(statement_end__gte=models.F("statement_start")), name="bank_statement_end_after_start"),
        ),
        migrations.CreateModel(
            name="BankStatementLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_date", models.DateField()),
                ("description", models.CharField(max_length=255)),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("matched_journal_line", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="matched_bank_statement_line", to="ledger.journalline")),
                ("statement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="ledger.bankstatement")),
            ],
            options={"ordering": ["transaction_date", "id"]},
        ),
        migrations.AddConstraint(
            model_name="bankstatementline",
            constraint=models.CheckConstraint(condition=~Q(amount=0), name="bank_statement_line_nonzero"),
        ),
    ]
