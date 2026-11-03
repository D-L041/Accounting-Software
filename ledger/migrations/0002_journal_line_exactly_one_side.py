from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("ledger", "0001_initial")]

    operations = [
        migrations.AddConstraint(
            model_name="journalline",
            constraint=models.CheckConstraint(
                condition=(Q(debit__gt=0, credit=0) | Q(credit__gt=0, debit=0)),
                name="journal_line_exactly_one_side",
            ),
        ),
    ]
