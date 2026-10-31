import hashlib
import json
import uuid

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OfflineSyncReceipt, School, SchoolMembership
from auditlog.services import record_event


class OfflineExpenseSyncView(APIView):
    """Accept allow-listed non-posting drafts from the encrypted outbox."""
    permission_classes = [permissions.IsAuthenticated]

    write_roles = {
        SchoolMembership.Role.OWNER,
        SchoolMembership.Role.ADMIN,
        SchoolMembership.Role.ACCOUNTANT,
        SchoolMembership.Role.BURSAR,
    }
    allowed_fields = {
        "expense": {
            "supplier", "category", "period", "expense_date", "description",
            "amount", "payment_method", "reference",
        },
        "purchase_order": {
            "supplier", "period", "order_date", "expected_date", "description", "lines",
        },
    }

    def post(self, request, school_pk):
        school = get_object_or_404(
            School.objects.filter(
                memberships__user=request.user,
                memberships__is_active=True,
                is_active=True,
            ).distinct(),
            pk=school_pk,
        )
        membership = SchoolMembership.objects.filter(
            school=school, user=request.user, is_active=True
        ).first()
        if not membership or membership.role not in self.write_roles:
            raise PermissionDenied("Your school role does not permit offline draft capture.")

        try:
            idempotency_key = uuid.UUID(str(request.data.get("idempotency_key")))
        except (ValueError, TypeError, AttributeError):
            raise ValidationError({"idempotency_key": "A valid UUID idempotency key is required."})

        resource_type = request.data.get("resource_type", "expense")
        if resource_type not in self.allowed_fields:
            raise ValidationError({"resource_type": "Only expense and purchase-order drafts can be synchronised."})
        payload = request.data.get("payload")
        if not isinstance(payload, dict) or not payload:
            raise ValidationError({"payload": "A non-empty draft object is required."})
        unknown = set(payload) - self.allowed_fields[resource_type]
        if unknown:
            raise ValidationError({"payload": f"Unsupported fields: {', '.join(sorted(unknown))}."})

        canonical = json.dumps(
            {"resource_type": resource_type, "payload": payload},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = OfflineSyncReceipt.objects.filter(
            school=school, user=request.user, idempotency_key=idempotency_key
        ).select_related("expense", "purchase_order").first()
        if existing:
            if existing.payload_hash != payload_hash:
                return Response(
                    {"status": "conflict", "detail": "This idempotency key was already used for different draft data."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response({
                "status": "already_applied",
                "resource_type": resource_type,
                "expense_id": existing.expense_id,
                "purchase_order_id": existing.purchase_order_id,
            }, status=status.HTTP_200_OK)

        from expenses.serializers import ExpenseSerializer, PurchaseOrderSerializer
        serializer_class = ExpenseSerializer if resource_type == "expense" else PurchaseOrderSerializer
        try:
            with transaction.atomic():
                serializer = serializer_class(
                    data=payload, context={"school": school, "request": request},
                )
                serializer.is_valid(raise_exception=True)
                if resource_type == "expense":
                    instance = serializer.save(school=school)
                    receipt_fields = {"expense": instance}
                    entity_type, action = "Expense", "OFFLINE_EXPENSE_DRAFT_SYNCED"
                    number = instance.expense_number
                else:
                    instance = serializer.save()
                    receipt_fields = {"purchase_order": instance}
                    entity_type, action = "PurchaseOrder", "OFFLINE_PURCHASE_ORDER_DRAFT_SYNCED"
                    number = instance.order_number
                OfflineSyncReceipt.objects.create(
                    school=school, user=request.user, idempotency_key=idempotency_key,
                    payload_hash=payload_hash, **receipt_fields,
                )
                record_event(
                    school=school, actor=request.user, action=action,
                    entity_type=entity_type, entity_id=instance.pk,
                    summary=f"Synchronised offline draft {number}",
                )
        except IntegrityError:
            existing = OfflineSyncReceipt.objects.filter(
                school=school, user=request.user, idempotency_key=idempotency_key
            ).select_related("expense", "purchase_order").first()
            if not existing:
                raise
            if existing.payload_hash != payload_hash:
                return Response(
                    {"status": "conflict", "detail": "This idempotency key was already used for different draft data."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response({
                "status": "already_applied",
                "resource_type": resource_type,
                "expense_id": existing.expense_id,
                "purchase_order_id": existing.purchase_order_id,
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "accepted", "resource_type": resource_type,
            "expense_id": instance.pk if resource_type == "expense" else None,
            "purchase_order_id": instance.pk if resource_type == "purchase_order" else None,
            "reference": number,
        }, status=status.HTTP_201_CREATED)
