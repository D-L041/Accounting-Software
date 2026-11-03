import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("daraja", "0001_initial"),
        ("billing", "0004_credit_notes_and_refunds"),
    ]

    operations = [
        migrations.AddField(
            model_name="c2bnotification",
            name="matched_invoice",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="c2b_notifications", to="billing.invoice"),
        ),
        migrations.AddField(
            model_name="c2bnotification",
            name="payment",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="c2b_notification", to="billing.payment"),
        ),
        migrations.AddField(
            model_name="c2bnotification",
            name="reconciled_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reconciled_c2b_notifications", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="c2bnotification",
            name="reconciled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
