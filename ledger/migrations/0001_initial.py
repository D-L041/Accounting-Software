# Generated for the initial financial ledger foundation.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="FinancialPeriod", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),("name", models.CharField(max_length=80, unique=True)),("starts_on", models.DateField()),("ends_on", models.DateField()),("is_locked", models.BooleanField(default=False))]),
        migrations.CreateModel(name="Account", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),("code", models.CharField(max_length=20, unique=True)),("name", models.CharField(max_length=120)),("category", models.CharField(choices=[("ASSET", "Asset"),("LIABILITY", "Liability"),("EQUITY", "Equity/Fund"),("INCOME", "Income"),("EXPENSE", "Expense")], max_length=12)),("is_active", models.BooleanField(default=True))]),
        migrations.CreateModel(name="JournalEntry", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),("reference", models.CharField(max_length=40, unique=True)),("description", models.CharField(max_length=255)),("entry_date", models.DateField(default=django.utils.timezone.localdate)),("posted", models.BooleanField(default=False)),("posted_at", models.DateTimeField(blank=True, null=True)),("created_at", models.DateTimeField(auto_now_add=True)),("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ledger.financialperiod"))]),
        migrations.CreateModel(name="JournalLine", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),("description", models.CharField(blank=True, max_length=255)),("debit", models.DecimalField(decimal_places=2, default=0, max_digits=14)),("credit", models.DecimalField(decimal_places=2, default=0, max_digits=14)),("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ledger.account")),("entry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="ledger.journalentry"))], options={"constraints":[models.CheckConstraint(condition=models.Q(("debit__gte",0)),name="journal_debit_nonnegative"),models.CheckConstraint(condition=models.Q(("credit__gte",0)),name="journal_credit_nonnegative")]}),
    ]
