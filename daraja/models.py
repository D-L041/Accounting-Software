from django.conf import settings
from django.db import models
from accounts.models import School
from billing.models import Invoice


class StkPushAttempt(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        CALLBACK_RECEIVED = "CALLBACK_RECEIVED", "Callback received"
        VERIFIED = "VERIFIED", "Verified"
        POSTED = "POSTED", "Payment posted"
        FAILED = "FAILED", "Failed"
        REVIEW = "REVIEW", "Manual review"

    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="stk_push_attempts")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="stk_push_attempts")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    phone_number = models.CharField(max_length=16)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    account_reference = models.CharField(max_length=40)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    mpesa_receipt_number = models.CharField(max_length=30, blank=True)
    result_code = models.CharField(max_length=20, blank=True)
    result_description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.INITIATED)
    payment = models.OneToOneField("billing.Payment", null=True, blank=True, on_delete=models.PROTECT, related_name="stk_attempt")
    callback_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "status"], name="daraja_stk_school_status"), models.Index(fields=["merchant_request_id"], name="daraja_stk_merchant_idx")]


class C2BNotification(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received - awaiting verification"
        VERIFIED = "VERIFIED", "Verified"
        POSTED = "POSTED", "Payment posted"
        REVIEW = "REVIEW", "Manual review"

    transaction_id = models.CharField(max_length=30, unique=True)
    business_shortcode = models.CharField(max_length=20)
    bill_reference = models.CharField(max_length=40, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    msisdn = models.CharField(max_length=20, blank=True)
    transaction_time = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    payload = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
