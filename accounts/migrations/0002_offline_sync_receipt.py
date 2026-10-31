import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OfflineSyncReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("idempotency_key", models.UUIDField()),
                ("payload_hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expense", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="offline_sync_receipts", to="expenses.expense")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offline_sync_receipts", to="accounts.school")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offline_sync_receipts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="offlinesyncreceipt",
            constraint=models.UniqueConstraint(fields=("school", "user", "idempotency_key"), name="unique_offline_sync_operation"),
        ),
        migrations.AddIndex(
            model_name="offlinesyncreceipt",
            index=models.Index(fields=["school", "created_at"], name="offline_sync_school_time_idx"),
        ),
    ]
