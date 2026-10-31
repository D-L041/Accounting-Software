from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                condition=~Q(transaction_reference=""),
                fields=("school", "method", "transaction_reference"),
                name="unique_payment_external_ref_school",
            ),
        ),
    ]
