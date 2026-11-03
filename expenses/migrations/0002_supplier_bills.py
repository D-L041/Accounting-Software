import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("expenses", "0001_initial"),
        ("ledger", "0004_bank_reconciliation"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupplierBill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bill_number", models.CharField(max_length=40)),
                ("supplier_invoice_number", models.CharField(max_length=100)),
                ("bill_date", models.DateField()),
                ("due_date", models.DateField()),
                ("description", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted for approval"), ("APPROVED", "Approved"), ("POSTED", "Posted"), ("PART_PAID", "Part paid"), ("PAID", "Paid")], default="DRAFT", max_length=12)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_supplier_bills", to=settings.AUTH_USER_MODEL)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_bills", to="expenses.expensecategory")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_supplier_bills", to=settings.AUTH_USER_MODEL)),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_supplier_bill", to="ledger.journalentry")),
                ("payable_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_bills", to="ledger.account")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_bills", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="supplier_bills", to="accounts.school")),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="submitted_supplier_bills", to=settings.AUTH_USER_MODEL)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bills", to="expenses.supplier")),
            ],
            options={"ordering": ["-bill_date", "-id"]},
        ),
        migrations.AddConstraint(model_name="supplierbill", constraint=models.UniqueConstraint(fields=("school", "bill_number"), name="unique_supplier_bill_number_school")),
        migrations.AddConstraint(model_name="supplierbill", constraint=models.UniqueConstraint(fields=("school", "supplier", "supplier_invoice_number"), name="unique_supplier_invoice_number_school")),
        migrations.AddConstraint(model_name="supplierbill", constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="supplier_bill_amount_positive")),
        migrations.AddConstraint(model_name="supplierbill", constraint=models.CheckConstraint(condition=Q(due_date__gte=models.F("bill_date")), name="supplier_bill_due_after_date")),
        migrations.CreateModel(
            name="SupplierBillPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("payment_method", models.CharField(choices=[("CASH", "Cash"), ("BANK", "Bank"), ("MPESA", "M-Pesa")], max_length=8)),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("bill", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="expenses.supplierbill")),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_supplier_bill_payment", to="ledger.journalentry")),
                ("payment_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_bill_payments", to="ledger.account")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_bill_payments", to="ledger.financialperiod")),
                ("recorded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["payment_date", "id"]},
        ),
        migrations.AddConstraint(model_name="supplierbillpayment", constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="supplier_bill_payment_amount_positive")),
    ]
