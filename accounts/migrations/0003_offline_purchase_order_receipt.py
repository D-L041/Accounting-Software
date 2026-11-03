import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_offline_sync_receipt"),
        ("expenses", "0004_purchase_orders"),
    ]

    operations = [
        migrations.AddField(
            model_name="offlinesyncreceipt",
            name="purchase_order",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="offline_sync_receipts", to="expenses.purchaseorder",
            ),
        ),
    ]
