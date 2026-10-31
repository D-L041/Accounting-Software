import json
import os

from django.core.exceptions import ImproperlyConfigured, ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
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


@csrf_exempt
def stk_callback(request):
    if request.method != "POST":
        return JsonResponse({"ResultCode": 1, "ResultDesc": "POST required"}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        result = process_stk_callback(payload)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON"}, status=400)
    except (DjangoValidationError, ImproperlyConfigured, IntegrityError) as exc:
        # Return success to Safaricom only after durable callback capture; failures remain for retry/reconciliation.
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Callback received for reconciliation"})
    return JsonResponse({"ResultCode": 0, "ResultDesc": f"Callback {result}"})


@csrf_exempt
def c2b_validation(request):
    if request.method != "POST":
        return JsonResponse({"ResultCode": "C2B00011", "ResultDesc": "POST required"}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        expected_shortcode = os.environ.get("DARAJA_SHORTCODE", "").strip()
        received_shortcode = str(payload.get("BusinessShortCode", "")).strip()
        bill_reference = str(payload.get("BillRefNumber", "")).strip()
        if not expected_shortcode or received_shortcode != expected_shortcode or not bill_reference:
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
        payload = json.loads(request.body.decode("utf-8"))
        transaction_id = str(payload["TransID"]).strip().upper()
        amount = payload["TransAmount"]
        bill_reference = str(payload["BillRefNumber"]).strip()
        shortcode = str(payload["BusinessShortCode"]).strip()
        expected_shortcode = os.environ.get("DARAJA_SHORTCODE", "").strip()
        if not expected_shortcode or shortcode != expected_shortcode:
            return JsonResponse({"ResultCode": "C2B00012", "ResultDesc": "Unrecognised business shortcode"}, status=403)
        if not transaction_id or not bill_reference or len(transaction_id) > 30:
            raise ValueError("Invalid C2B identifiers")
        C2BNotification.objects.get_or_create(transaction_id=transaction_id, defaults={
            "business_shortcode": shortcode, "bill_reference": bill_reference,
            "amount": amount, "msisdn": str(payload.get("MSISDN", "")),
            "transaction_time": str(payload.get("TransTime", "")), "payload": payload,
        })
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        return JsonResponse({"ResultCode": "C2B00012", "ResultDesc": "Invalid confirmation payload"}, status=400)
    # C2B is durably captured, but is not posted until a transaction-status verification and invoice match pass.
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
        invoice_refs = Invoice.objects.filter(school=school).values_list("invoice_number", flat=True)
        notifications = C2BNotification.objects.filter(
            bill_reference__in=invoice_refs
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
