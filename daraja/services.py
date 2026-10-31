import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_DOWN

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from billing.models import Invoice
from billing.services import record_payment
from .models import StkPushAttempt


def _config():
    values = {key: os.environ.get(key, "").strip() for key in (
        "DARAJA_ENV", "DARAJA_CONSUMER_KEY", "DARAJA_CONSUMER_SECRET",
        "DARAJA_SHORTCODE", "DARAJA_PASSKEY", "DARAJA_CALLBACK_URL",
    )}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ImproperlyConfigured("Missing Daraja configuration: " + ", ".join(missing))
    if values["DARAJA_ENV"] not in {"sandbox", "production"}:
        raise ImproperlyConfigured("DARAJA_ENV must be sandbox or production.")
    if not values["DARAJA_CALLBACK_URL"].startswith("https://"):
        raise ImproperlyConfigured("Daraja callback URL must use public HTTPS.")
    return values


def _base_url(config):
    return "https://sandbox.safaricom.co.ke" if config["DARAJA_ENV"] == "sandbox" else "https://api.safaricom.co.ke"


def _request(url, data=None, headers=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers or {}, method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValidationError("Safaricom Daraja could not be reached. No payment has been posted.") from exc


def _access_token(config):
    credentials = base64.b64encode(f'{config["DARAJA_CONSUMER_KEY"]}:{config["DARAJA_CONSUMER_SECRET"]}'.encode()).decode()
    result = _request(_base_url(config) + "/oauth/v1/generate?grant_type=client_credentials", headers={"Authorization": f"Basic {credentials}"})
    token = result.get("access_token")
    if not token:
        raise ValidationError("Daraja did not return an access token.")
    return token


def _timestamp():
    return timezone.localtime().strftime("%Y%m%d%H%M%S")


def _password(config, timestamp):
    raw = f'{config["DARAJA_SHORTCODE"]}{config["DARAJA_PASSKEY"]}{timestamp}'
    return base64.b64encode(raw.encode()).decode()


def normalize_phone(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif digits.startswith("7") or digits.startswith("1"):
        digits = "254" + digits
    if len(digits) != 12 or not digits.startswith("254"):
        raise ValidationError("Enter a valid Kenyan mobile number, e.g. 2547XXXXXXXX.")
    return digits


def initiate_stk_push(*, invoice, user, phone_number):
    config = _config()
    if invoice.status not in {Invoice.Status.ISSUED, Invoice.Status.PART_PAID} or invoice.balance <= 0:
        raise ValidationError("Only an issued invoice with an outstanding balance can receive an STK Push.")
    phone = normalize_phone(phone_number)
    amount = invoice.balance.quantize(Decimal("1"), rounding=ROUND_DOWN)
    if amount < 1:
        raise ValidationError("The outstanding balance must be at least KES 1 for an STK Push.")
    attempt = StkPushAttempt.objects.create(
        school=invoice.school, invoice=invoice, initiated_by=user, phone_number=phone,
        amount=amount, account_reference=invoice.invoice_number,
    )
    timestamp = _timestamp()
    payload = {
        "BusinessShortCode": config["DARAJA_SHORTCODE"], "Password": _password(config, timestamp),
        "Timestamp": timestamp, "TransactionType": os.environ.get("DARAJA_TRANSACTION_TYPE", "CustomerPayBillOnline"),
        "Amount": int(amount), "PartyA": phone, "PartyB": config["DARAJA_SHORTCODE"],
        "PhoneNumber": phone, "CallBackURL": config["DARAJA_CALLBACK_URL"],
        "AccountReference": invoice.invoice_number[:12], "TransactionDesc": f"School fees {invoice.invoice_number}"[:13],
    }
    result = _request(_base_url(config) + "/mpesa/stkpush/v1/processrequest", payload,
                      {"Authorization": f"Bearer {_access_token(config)}", "Content-Type": "application/json"})
    checkout_id = result.get("CheckoutRequestID")
    if not checkout_id:
        attempt.status = StkPushAttempt.Status.FAILED
        attempt.result_description = str(result.get("errorMessage") or result.get("ResponseDescription") or "Daraja rejected STK request")[:255]
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        raise ValidationError(attempt.result_description)
    attempt.merchant_request_id = str(result.get("MerchantRequestID", ""))[:100]
    attempt.checkout_request_id = checkout_id
    attempt.result_description = str(result.get("ResponseDescription", ""))[:255]
    attempt.save(update_fields=["merchant_request_id", "checkout_request_id", "result_description", "updated_at"])
    return attempt


def query_stk_push(attempt):
    config = _config()
    timestamp = _timestamp()
    payload = {
        "BusinessShortCode": config["DARAJA_SHORTCODE"], "Password": _password(config, timestamp),
        "Timestamp": timestamp, "CheckoutRequestID": attempt.checkout_request_id,
    }
    return _request(_base_url(config) + "/mpesa/stkpushquery/v1/query", payload,
                    {"Authorization": f"Bearer {_access_token(config)}", "Content-Type": "application/json"})


@transaction.atomic
def process_stk_callback(payload):
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    if not checkout_id:
        return "ignored"
    attempt = StkPushAttempt.objects.select_for_update().select_related("invoice", "school", "initiated_by").filter(checkout_request_id=checkout_id).first()
    if not attempt or attempt.status == StkPushAttempt.Status.POSTED:
        return "duplicate_or_unknown"
    attempt.callback_payload = payload
    attempt.result_code = str(callback.get("ResultCode", ""))[:20]
    attempt.result_description = str(callback.get("ResultDesc", ""))[:255]
    attempt.status = StkPushAttempt.Status.CALLBACK_RECEIVED
    attempt.save(update_fields=["callback_payload", "result_code", "result_description", "status", "updated_at"])
    if attempt.result_code != "0":
        attempt.status = StkPushAttempt.Status.FAILED
        attempt.save(update_fields=["status", "updated_at"])
        return "failed"
    # A callback alone is not trusted as proof of payment. Confirm with Daraja's STK query API.
    try:
        verification = query_stk_push(attempt)
    except (ValidationError, ImproperlyConfigured):
        attempt.status = StkPushAttempt.Status.REVIEW
        attempt.result_description = "Daraja STK Query was unavailable; manual verification required."
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        return "verification_unavailable"
    if str(verification.get("ResultCode")) != "0":
        attempt.status = StkPushAttempt.Status.REVIEW
        attempt.result_description = "STK query did not confirm success; manual review required."
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        return "unverified"
    metadata = callback.get("CallbackMetadata", {}).get("Item", [])
    values = {item.get("Name"): item.get("Value") for item in metadata if isinstance(item, dict)}
    receipt = str(values.get("MpesaReceiptNumber", "")).strip().upper()
    try:
        received_amount = Decimal(str(values.get("Amount", "0"))).quantize(Decimal("0.01"))
        phone = normalize_phone(values.get("PhoneNumber", attempt.phone_number))
    except (ValidationError, ArithmeticError, ValueError):
        attempt.status = StkPushAttempt.Status.REVIEW
        attempt.result_description = "Callback metadata was invalid; manual verification required."
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        return "invalid_metadata"
    if not receipt or received_amount != attempt.amount or phone != attempt.phone_number:
        attempt.status = StkPushAttempt.Status.REVIEW
        attempt.result_description = "Callback amount, receipt or payer phone did not match the STK request."
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        return "mismatch"
    invoice = Invoice.objects.select_for_update().get(pk=attempt.invoice_id)
    if invoice.balance < received_amount or invoice.balance <= 0:
        attempt.status = StkPushAttempt.Status.REVIEW
        attempt.result_description = "Invoice balance changed after STK request; manual allocation review required."
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        return "balance_changed"
    try:
        payment = record_payment(
            school=attempt.school, student=invoice.student, payment_date=timezone.localdate(),
            method="MPESA", amount=received_amount,
            allocations=[{"invoice_id": invoice.pk, "amount": received_amount}],
            user=attempt.initiated_by, transaction_reference=receipt,
            notes=f"Daraja STK Push {attempt.checkout_request_id}",
        )
    except (ValidationError, IntegrityError):
        attempt.status = StkPushAttempt.Status.REVIEW
        attempt.result_description = "Payment could not be posted safely; manual reconciliation required."
        attempt.save(update_fields=["status", "result_description", "updated_at"])
        return "posting_review"
    attempt.payment = payment
    attempt.mpesa_receipt_number = receipt
    attempt.status = StkPushAttempt.Status.POSTED
    attempt.save(update_fields=["payment", "mpesa_receipt_number", "status", "updated_at"])
    return "posted"


@transaction.atomic
def reconcile_c2b_notification(*, notification_id, school, user, invoice_id, confirm_statement_match):
    from django.core.exceptions import ValidationError
    from accounts.models import SchoolMembership
    from auditlog.services import record_event
    from billing.models import Payment
    from .models import C2BNotification

    membership = SchoolMembership.objects.filter(
        school=school, user=user, is_active=True
    ).first()
    allowed = {
        SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN,
        SchoolMembership.Role.ACCOUNTANT, SchoolMembership.Role.BURSAR,
    }
    if not membership or membership.role not in allowed:
        raise ValidationError("Your school role cannot reconcile M-Pesa payments.")
    if confirm_statement_match is not True:
        raise ValidationError("Confirm that the transaction has been independently matched to the Safaricom statement.")
    notification = C2BNotification.objects.select_for_update(of=("self",)).select_related("matched_invoice").get(pk=notification_id)
    if notification.status == C2BNotification.Status.POSTED:
        if notification.matched_invoice_id == invoice_id and notification.matched_invoice.school_id == school.id:
            return notification
        raise ValidationError("This M-Pesa transaction has already been reconciled to another school or invoice.")
    if notification.payment_id:
        raise ValidationError("This M-Pesa transaction is already linked to a payment.")
    invoice = Invoice.objects.select_for_update().select_related("student", "period").get(
        pk=invoice_id, school=school
    )
    if invoice.invoice_number.strip().upper() != notification.bill_reference.strip().upper():
        raise ValidationError("The M-Pesa account reference does not exactly match this invoice number.")
    if Invoice.objects.filter(invoice_number__iexact=invoice.invoice_number).exclude(school=school).exists():
        raise ValidationError("This invoice number is duplicated in another school. Resolve the school/paybill mapping before reconciling this transaction.")
    if invoice.status not in {Invoice.Status.ISSUED, Invoice.Status.PART_PAID}:
        raise ValidationError("Only an issued invoice with an outstanding balance can receive this payment.")
    amount = notification.amount.quantize(Decimal("0.01"))
    if amount <= 0 or amount > invoice.balance:
        raise ValidationError("The M-Pesa amount must be positive and cannot exceed the invoice balance.")
    if Payment.objects.filter(
        school=school, method=Payment.Method.MPESA,
        transaction_reference=notification.transaction_id,
    ).exists():
        raise ValidationError("This M-Pesa transaction ID has already been recorded.")
    payment = record_payment(
        school=school, student=invoice.student, payment_date=timezone.localdate(),
        method=Payment.Method.MPESA, amount=amount,
        allocations=[{"invoice_id": invoice.pk, "amount": amount}],
        user=user, transaction_reference=notification.transaction_id,
        notes=f"Daraja C2B {notification.transaction_id}",
    )
    notification.matched_invoice = invoice
    notification.payment = payment
    notification.reconciled_by = user
    notification.reconciled_at = timezone.now()
    notification.status = C2BNotification.Status.POSTED
    notification.save(update_fields=[
        "matched_invoice", "payment", "reconciled_by", "reconciled_at", "status"
    ])
    record_event(
        school=school, actor=user, action="MPESA_C2B_RECONCILED",
        entity_type="C2BNotification", entity_id=notification.pk,
        summary=f"Reconciled M-Pesa transaction {notification.transaction_id}",
        metadata={"invoice_id": invoice.pk, "payment_id": payment.pk, "amount": str(amount)},
    )
    return notification
