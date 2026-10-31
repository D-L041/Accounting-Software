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
    """Accept only expense drafts from the encrypted offline outbox; never post a journal."""
    permission_classes = [permissions.IsAuthenticated]

    write_roles = {
        SchoolMembership.Role.OWNER,
        SchoolMembership.Role.ADMIN,
        SchoolMembership.Role.ACCOUNTANT,
        SchoolMembership.Role.BURSAR,
    }
    allowed_fields = {
        "supplier", "category", "period", "expense_date", "description",
        "amount", "payment_method", "reference",
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
            raise PermissionDenied("Your school role does not permit offline expense capture.")

        raw_key = request.data.get("idempotency_key")
        try:
            idempotency_key = uuid.UUID(str(raw_key))
        except (ValueError, TypeError, AttributeError):
            raise ValidationError({"idempotency_key": "A valid UUID idempotency key is required."})

        payload = request.data.get("payload")
        if not isinstance(payload, dict) or not payload:
            raise ValidationError({"payload": "A non-empty expense draft object is required."})
        unknown = set(payload) - self.allowed_fields
        if unknown:
            raise ValidationError({"payload": f"Unsupported fields: {', '.join(sorted(unknown))}."})

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = OfflineSyncReceipt.objects.filter(
            school=school, user=request.user, idempotency_key=idempotency_key
        ).select_related("expense").first()
        if existing:
            if existing.payload_hash != payload_hash:
                return Response(
                    {"status": "conflict", "detail": "This idempotency key was already used for different draft data."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"status": "already_applied", "expense_id": existing.expense_id},
                status=status.HTTP_200_OK,
            )

        from expenses.serializers import ExpenseSerializer

        try:
            with transaction.atomic():
                serializer = ExpenseSerializer(
                    data=payload,
                    context={"school": school, "request": request},
                )
                serializer.is_valid(raise_exception=True)
                expense = serializer.save(school=school)
                OfflineSyncReceipt.objects.create(
                    school=school,
                    user=request.user,
                    idempotency_key=idempotency_key,
                    payload_hash=payload_hash,
                    expense=expense,
                )
                record_event(
                    school=school,
                    actor=request.user,
                    action="OFFLINE_EXPENSE_DRAFT_SYNCED",
                    entity_type="Expense",
                    entity_id=expense.pk,
                    summary=f"Synced offline expense draft {expense.expense_number}",
                )
        except IntegrityError:
            # A simultaneous retry may win the unique idempotency constraint.
            existing = OfflineSyncReceipt.objects.filter(
                school=school, user=request.user, idempotency_key=idempotency_key
            ).select_related("expense").first()
            if not existing:
                raise
            if existing.payload_hash != payload_hash:
                return Response(
                    {"status": "conflict", "detail": "This idempotency key was already used for different draft data."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"status": "already_applied", "expense_id": existing.expense_id},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"status": "accepted", "expense_id": expense.pk, "expense_number": expense.expense_number},
            status=status.HTTP_201_CREATED,
        )
