import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("billing", "0002_unique_payment_external_reference"),
        ("ledger", "0003_school_scope_ledger"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeeSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term_name", models.CharField(max_length=40)),
                ("invoice_date", models.DateField()),
                ("due_date", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fee_schedules", to="accounts.academicyear")),
                ("classroom", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fee_schedules", to="accounts.classroom")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fee_schedules", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fee_schedules", to="accounts.school")),
            ],
            options={"ordering": ["-academic_year__starts_on", "classroom__name", "term_name"]},
        ),
        migrations.AddConstraint(
            model_name="feeschedule",
            constraint=models.UniqueConstraint(fields=("school", "academic_year", "classroom", "term_name"), name="unique_class_term_fee_schedule"),
        ),
        migrations.AddConstraint(
            model_name="feeschedule",
            constraint=models.CheckConstraint(condition=Q(("due_date__gte", models.F("invoice_date"))), name="fee_schedule_due_after_invoice"),
        ),
        migrations.CreateModel(
            name="FeeScheduleLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("fee_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="schedule_lines", to="billing.feeitem")),
                ("schedule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="billing.feeschedule")),
            ],
        ),
        migrations.AddConstraint(
            model_name="feescheduleline",
            constraint=models.UniqueConstraint(fields=("schedule", "fee_item"), name="unique_fee_item_per_schedule"),
        ),
        migrations.AddConstraint(
            model_name="feescheduleline",
            constraint=models.CheckConstraint(condition=Q(("amount__gt", 0)), name="fee_schedule_line_amount_positive"),
        ),
        migrations.AddField(
            model_name="invoice",
            name="fee_schedule",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generated_invoices", to="billing.feeschedule"),
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(condition=Q(("fee_schedule__isnull", False)), fields=("school", "student", "fee_schedule"), name="unique_student_fee_schedule_invoice"),
        ),
    ]
