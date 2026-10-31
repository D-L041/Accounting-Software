import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("billing", "0004_credit_notes_and_refunds"),
    ]
    operations = [
        migrations.CreateModel(name="StkPushAttempt", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("phone_number", models.CharField(max_length=16)),
            ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
            ("account_reference", models.CharField(max_length=40)),
            ("merchant_request_id", models.CharField(blank=True, max_length=100)),
            ("checkout_request_id", models.CharField(blank=True, max_length=100, null=True, unique=True)),
            ("mpesa_receipt_number", models.CharField(blank=True, max_length=30)),
            ("result_code", models.CharField(blank=True, max_length=20)),
            ("result_description", models.CharField(blank=True, max_length=255)),
            ("status", models.CharField(choices=[("INITIATED", "Initiated"), ("CALLBACK_RECEIVED", "Callback received"), ("VERIFIED", "Verified"), ("POSTED", "Payment posted"), ("FAILED", "Failed"), ("REVIEW", "Manual review")], default="INITIATED", max_length=24)),
            ("callback_payload", models.JSONField(blank=True, default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("initiated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stk_push_attempts", to="billing.invoice")),
            ("payment", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="stk_attempt", to="billing.payment")),
            ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stk_push_attempts", to="accounts.school")),
        ], options={"ordering": ["-created_at"]}),
        migrations.AddIndex(model_name="stkpushattempt", index=models.Index(fields=["school", "status"], name="daraja_stk_school_status")),
        migrations.AddIndex(model_name="stkpushattempt", index=models.Index(fields=["merchant_request_id"], name="daraja_stk_merchant_idx")),
        migrations.CreateModel(name="C2BNotification", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("transaction_id", models.CharField(max_length=30, unique=True)),
            ("business_shortcode", models.CharField(max_length=20)),
            ("bill_reference", models.CharField(db_index=True, max_length=40)),
            ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
            ("msisdn", models.CharField(blank=True, max_length=20)),
            ("transaction_time", models.CharField(blank=True, max_length=20)),
            ("status", models.CharField(choices=[("RECEIVED", "Received - awaiting verification"), ("VERIFIED", "Verified"), ("POSTED", "Payment posted"), ("REVIEW", "Manual review")], default="RECEIVED", max_length=16)),
            ("payload", models.JSONField(blank=True, default=dict)),
            ("received_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-received_at"]}),
    ]
