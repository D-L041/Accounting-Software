import json
import os
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ImproperlyConfigured, ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import School, SchoolMembership
from billing.models import Invoice
from .models import C2BNotification, StkPushAttempt
from .services import initiate_stk_push, process_stk_callback, reconcile_c2b_notification


class StkPushView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, school_pk):
        member = SchoolMembership.objects.filter(school_id=school_pk, user=request.user, is_active=True).first()
        if not member or member.role not in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN, SchoolMembership.Role.ACCOUNTANT, SchoolMembership.Role.BURSAR}:
            raise PermissionDenied("Your school role cannot initiate parent payments.")
        invoice = Invoice.objects.filter(school_id=school_pk).select_related("school", "student").filter(pk=request.data.get("invoice")).first()
        if not invoice:
            raise ValidationError({"invoice": "Invoice was not found in this school."})
        try:
            attempt = initiate_stk_push(invoice=invoice, user=request.user, phone_number=request.data.get("phone_number", ""))
        except (DjangoValidationError, ImproperlyConfigured) as exc:
            raise ValidationError(getattr(exc, "messages", [str(exc)])) from exc
        return Response({"id": attempt.pk, "checkout_request_id": attempt.checkout_request_id, "status": attempt.status, "amount": str(attempt.amount)}, status=status.HTTP_201_CREATED)


MAX_CALLBACK_BODY_BYTES = 64 * 1024


def _decode_callback_payload(request):
    if len(request.body) > MAX_CALLBACK_BODY_BYTES:
        raise ValueError("Callback payload is too large.")
    payload = json.loads(request.body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Callback payload must be a JSON object.")
    return payload


@csrf_exempt
def stk_callback(request):
    if request.method != "POST":
        return JsonResponse({"ResultCode": 1, "ResultDesc": "POST required"}, status=405)
    try:
        payload = _decode_callback_payload(request)
        result = process_stk_callback(payload)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid callback payload"}, status=400)
    except (DjangoValidationError, ImproperlyConfigured, IntegrityError):
        # Payment posting remains protected by STK Query verification in the service.
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback received for reconciliation"})
    return JsonResponse({"ResultCode": 0, "ResultDesc": f"Callback {result}"})


@csrf_exempt
def c2b_validation(request):
    if request.method != "POST":
        return JsonResponse({"ResultCode": "C2B00011", "ResultDesc": "POST required"}, status=405)
    try:
        payload = _decode_callback_payload(request)
        expected_shortcode = os.environ.get("DARAJA_SHORTCODE", "").strip()
        received_shortcode = str(payload.get("BusinessShortCode", "")).strip()
        bill_reference = str(payload.get("BillRefNumber", "")).strip()
        if (
            not expected_shortcode
            or received_shortcode != expected_shortcode
            or not bill_reference
            or len(bill_reference) > 40
        ):
            return JsonResponse({"ResultCode": "C2B00012", "ResultDesc": "Invalid shortcode or bill reference"})
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ResultCode": "C2B00012", "ResultDesc": "Invalid validation payload"}, status=400)
    # Validation acknowledges the configured paybill only; allocation occurs after confirmation verification.
    return JsonResponse({"ResultCode": "0", "ResultDesc": "Accepted for confirmation and reconciliation"})


@csrf_exempt
@transaction.atomic
def c2b_confirmation(request):
    if request.method != "POST":
        return JsonResponse({"ResultCode": "C2B00011", "ResultDesc": "POST required"}, status=405)
    try:
        payload = _decode_callback_payload(request)
        transaction_id = str(payload["TransID"]).strip().upper()
        amount = Decimal(str(payload["TransAmount"]))
        bill_reference = str(payload["BillRefNumber"]).strip()
        shortcode = str(payload["BusinessShortCode"]).strip()
        msisdn = str(payload.get("MSISDN", "")).strip()
        transaction_time = str(payload.get("TransTime", "")).strip()
        expected_shortcode = os.environ.get("DARAJA_SHORTCODE", "").strip()
        if not expected_shortcode or shortcode != expected_shortcode:
            return JsonResponse({"ResultCode": "C2B00012", "ResultDesc": "Unrecognised business shortcode"}, status=403)
        if (
            not transaction_id or len(transaction_id) > 30
            or not bill_reference or len(bill_reference) > 40
            or len(shortcode) > 20 or len(msisdn) > 20 or len(transaction_time) > 20
            or not amount.is_finite() or amount <= 0
            or amount.quantize(Decimal("0.01")) != amount
            or amount > Decimal("999999999999.99")
        ):
            raise ValueError("Invalid C2B confirmation fields")
        C2BNotification.objects.get_or_create(transaction_id=transaction_id, defaults={
            "business_shortcode": shortcode, "bill_reference": bill_reference,
            "amount": amount, "msisdn": msisdn,
            "transaction_time": transaction_time, "payload": payload,
        })
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, InvalidOperation):
        return JsonResponse({"ResultCode": "C2B00012", "ResultDesc": "Invalid confirmation payload"}, status=400)
    # C2B is durably captured, but is not posted until a statement match is independently confirmed.
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Confirmation captured for verification"})


class C2BReconcileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_school(self, request, school_pk):
        school = School.objects.filter(
            pk=school_pk, is_active=True,
            memberships__user=request.user, memberships__is_active=True,
        ).first()
        if not school:
            raise PermissionDenied("You do not have access to this school.")
        return school

    def get(self, request, school_pk, notification_pk=None):
        school = self.get_school(request, school_pk)
        other_school_refs = Invoice.objects.exclude(school=school).values_list("invoice_number", flat=True)
        unique_invoice_refs = Invoice.objects.filter(school=school).exclude(
            invoice_number__in=other_school_refs
        ).values_list("invoice_number", flat=True)
        notifications = C2BNotification.objects.filter(
            Q(bill_reference__in=unique_invoice_refs) | Q(matched_invoice__school=school)
        ).select_related("matched_invoice", "payment", "reconciled_by")
        if notification_pk is not None:
            notifications = notifications.filter(pk=notification_pk)
        return Response([{
            "id": item.pk, "transaction_id": item.transaction_id,
            "bill_reference": item.bill_reference, "amount": str(item.amount),
            "msisdn": item.msisdn, "transaction_time": item.transaction_time,
            "status": item.status, "invoice_id": item.matched_invoice_id,
            "payment_id": item.payment_id,
            "receipt_number": item.payment.receipt_number if item.payment_id else None,
        } for item in notifications[:200]])

    def post(self, request, school_pk, notification_pk):
        school = self.get_school(request, school_pk)
        try:
            notification = reconcile_c2b_notification(
                notification_id=notification_pk, school=school, user=request.user,
                invoice_id=request.data.get("invoice_id"),
                confirm_statement_match=request.data.get("confirm_statement_match"),
            )
        except (DjangoValidationError, IntegrityError) as exc:
            raise ValidationError(getattr(exc, "messages", [str(exc)])) from exc
        return Response({
            "id": notification.pk, "transaction_id": notification.transaction_id,
            "status": notification.status, "invoice_id": notification.matched_invoice_id,
            "payment_id": notification.payment_id,
            "receipt_number": notification.payment.receipt_number if notification.payment_id else None,
        }, status=status.HTTP_200_OK)
