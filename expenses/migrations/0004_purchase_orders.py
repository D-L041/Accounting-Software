import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from decimal import Decimal
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("expenses", "0003_expensebudget"),
        ("accounts", "0001_initial"),
        ("ledger", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcurementApprovalRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("min_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("step_number", models.PositiveSmallIntegerField(default=1)),
                ("approver_role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "Administrator"), ("ACCOUNTANT", "Accountant")], max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="procurement_approval_rules", to="accounts.school")),
            ],
            options={"ordering": ["min_amount", "step_number"]},
        ),
        migrations.AddConstraint(model_name="procurementapprovalrule", constraint=models.UniqueConstraint(fields=("school", "min_amount", "step_number"), name="unique_procurement_rule_step")),
        migrations.AddConstraint(model_name="procurementapprovalrule", constraint=models.CheckConstraint(condition=Q(min_amount__gte=0), name="procurement_rule_min_nonnegative")),
        migrations.AddConstraint(model_name="procurementapprovalrule", constraint=models.CheckConstraint(condition=Q(step_number__gte=1), name="procurement_rule_step_positive")),
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.CharField(max_length=40)),
                ("order_date", models.DateField()),
                ("expected_date", models.DateField(blank=True, null=True)),
                ("description", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CLOSED", "Closed")], default="DRAFT", max_length=12)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_purchase_orders", to=settings.AUTH_USER_MODEL)),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purchase_orders", to="accounts.school")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders", to="expenses.supplier")),
            ],
            options={"ordering": ["-order_date", "-id"]},
        ),
        migrations.AddConstraint(model_name="purchaseorder", constraint=models.UniqueConstraint(fields=("school", "order_number"), name="unique_purchase_order_number_school")),
        migrations.CreateModel(
            name="PurchaseOrderLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=255)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=14)),
                ("purchase_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="expenses.purchaseorder")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(model_name="purchaseorderline", constraint=models.CheckConstraint(condition=Q(quantity__gt=0), name="purchase_order_line_qty_positive")),
        migrations.AddConstraint(model_name="purchaseorderline", constraint=models.CheckConstraint(condition=Q(unit_cost__gte=0), name="purchase_order_line_cost_nonnegative")),
        migrations.CreateModel(
            name="PurchaseOrderApproval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("step_number", models.PositiveSmallIntegerField()),
                ("approver_role", models.CharField(max_length=20)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("purchase_order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approvals", to="expenses.purchaseorder")),
            ],
            options={"ordering": ["step_number"]},
        ),
        migrations.AddConstraint(model_name="purchaseorderapproval", constraint=models.UniqueConstraint(fields=("purchase_order", "step_number"), name="unique_purchase_order_approval_step")),
    ]
