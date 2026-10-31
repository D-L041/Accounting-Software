import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("accounts", "0001_initial"),
        ("ledger", "0003_school_scope_ledger"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeeItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("income_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fee_items", to="ledger.account")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fee_items", to="accounts.school")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SchoolBillingSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_prefix", models.CharField(default="INV", max_length=12)),
                ("receipt_prefix", models.CharField(default="RCT", max_length=12)),
                ("bank_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="billing_bank_settings", to="ledger.account")),
                ("cash_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="billing_cash_settings", to="ledger.account")),
                ("receivables_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="billing_receivables_settings", to="ledger.account")),
                ("school", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="billing_settings", to="accounts.school")),
            ],
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_number", models.CharField(max_length=40)),
                ("invoice_date", models.DateField()),
                ("due_date", models.DateField()),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("ISSUED", "Issued"), ("PART_PAID", "Part paid"), ("PAID", "Paid"), ("VOID", "Void")], default="DRAFT", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="accounts.academicyear")),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_invoice", to="ledger.journalentry")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invoices", to="accounts.school")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="invoices", to="accounts.student")),
            ],
            options={"ordering": ["-invoice_date", "-id"]},
        ),
        migrations.CreateModel(
            name="InvoiceLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, max_length=255)),
                ("quantity", models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=10)),
                ("unit_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("fee_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="billing.feeitem")),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="billing.invoice")),
            ],
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("receipt_number", models.CharField(max_length=40)),
                ("payment_date", models.DateField()),
                ("method", models.CharField(choices=[("CASH", "Cash"), ("BANK", "Bank"), ("MPESA", "M-Pesa")], max_length=8)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("transaction_reference", models.CharField(blank=True, max_length=100)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_payment", to="ledger.journalentry")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fee_payments", to="accounts.school")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fee_payments", to="accounts.student")),
            ],
            options={"ordering": ["-payment_date", "-id"]},
        ),
        migrations.CreateModel(
            name="PaymentAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="billing.invoice")),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="allocations", to="billing.payment")),
            ],
        ),
        migrations.AddConstraint(
            model_name="feeitem",
            constraint=models.UniqueConstraint(fields=("school", "code"), name="unique_fee_item_code_school"),
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(fields=("school", "invoice_number"), name="unique_invoice_number_school"),
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.CheckConstraint(condition=models.Q(("due_date__gte", models.F("invoice_date"))), name="invoice_due_after_issue"),
        ),
        migrations.AddConstraint(
            model_name="invoiceline",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gt", 0)), name="invoice_line_quantity_positive"),
        ),
        migrations.AddConstraint(
            model_name="invoiceline",
            constraint=models.CheckConstraint(condition=models.Q(("unit_amount__gte", 0)), name="invoice_line_unit_amount_nonnegative"),
        ),
        migrations.AddConstraint(
            model_name="invoiceline",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gte", 0)), name="invoice_line_amount_nonnegative"),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(fields=("school", "receipt_number"), name="unique_receipt_number_school"),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payment_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="paymentallocation",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payment_allocation_positive"),
        ),
        migrations.AddConstraint(
            model_name="paymentallocation",
            constraint=models.UniqueConstraint(fields=("payment", "invoice"), name="unique_payment_invoice_allocation"),
        ),
    ]
