import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0003_fee_schedules_and_bulk_invoicing"),
        ("ledger", "0004_bank_reconciliation"),
    ]

    operations = [
        migrations.CreateModel(
            name="CreditNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credit_note_number", models.CharField(max_length=40)),
                ("credit_date", models.DateField()),
                ("reason", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted")], default="DRAFT", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="credit_notes", to="billing.invoice")),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_credit_note", to="ledger.journalentry")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="credit_notes", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credit_notes", to="accounts.school")),
            ],
            options={"ordering": ["-credit_date", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="creditnote",
            constraint=models.UniqueConstraint(fields=("school", "credit_note_number"), name="unique_credit_note_number_school"),
        ),
        migrations.CreateModel(
            name="CreditNoteLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("credit_note", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="billing.creditnote")),
                ("invoice_line", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="credit_note_lines", to="billing.invoiceline")),
            ],
        ),
        migrations.AddConstraint(
            model_name="creditnoteline",
            constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="credit_note_line_amount_positive"),
        ),
        migrations.CreateModel(
            name="PaymentRefund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("refund_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_refunds", to="billing.invoice")),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_payment_refund", to="ledger.journalentry")),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refunds", to="billing.payment")),
                ("payment_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_refunds", to="ledger.account")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_refunds", to="ledger.financialperiod")),
                ("recorded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-refund_date", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="paymentrefund",
            constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="payment_refund_amount_positive"),
        ),
    ]
