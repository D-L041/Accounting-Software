import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("accounts", "0001_initial"),
        ("billing", "0001_initial"),
        ("ledger", "0003_school_scope_ledger"),
    ]

    operations = [
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("contact_person", models.CharField(blank=True, max_length=120)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("tax_pin", models.CharField(blank=True, max_length=20)),
                ("address", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="suppliers", to="accounts.school")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ExpenseCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("expense_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expense_categories", to="ledger.account")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expense_categories", to="accounts.school")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expense_number", models.CharField(max_length=40)),
                ("expense_date", models.DateField()),
                ("description", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("payment_method", models.CharField(choices=[("CASH", "Cash"), ("BANK", "Bank"), ("MPESA", "M-Pesa")], max_length=8)),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted")], default="DRAFT", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses", to="expenses.expensecategory")),
                ("journal_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_expense", to="ledger.journalentry")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="accounts.school")),
                ("supplier", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="expenses", to="expenses.supplier")),
            ],
            options={"ordering": ["-expense_date", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="supplier",
            constraint=models.UniqueConstraint(fields=("school", "name"), name="unique_supplier_name_school"),
        ),
        migrations.AddConstraint(
            model_name="expensecategory",
            constraint=models.UniqueConstraint(fields=("school", "code"), name="unique_expense_category_code_school"),
        ),
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.UniqueConstraint(fields=("school", "expense_number"), name="unique_expense_number_school"),
        ),
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="expense_amount_positive"),
        ),
    ]
