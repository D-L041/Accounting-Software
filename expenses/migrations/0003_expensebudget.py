import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("expenses", "0002_supplier_bills"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpenseBudget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("budget_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="budgets", to="expenses.expensecategory")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expense_budgets", to="ledger.financialperiod")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expense_budgets", to="accounts.school")),
            ],
            options={"ordering": ["category__name"]},
        ),
        migrations.AddConstraint(
            model_name="expensebudget",
            constraint=models.UniqueConstraint(fields=("school", "period", "category"), name="unique_expense_budget_school_period_category"),
        ),
        migrations.AddConstraint(
            model_name="expensebudget",
            constraint=models.CheckConstraint(condition=Q(budget_amount__gte=0), name="expense_budget_nonnegative"),
        ),
    ]
