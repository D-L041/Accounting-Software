from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import CreditNote, FeeItem, FeeSchedule, Invoice, Payment, PaymentRefund, SchoolBillingSettings
from .serializers import CreditNoteSerializer, FeeItemSerializer, FeeScheduleSerializer, InvoiceSerializer, PaymentRefundInputSerializer, PaymentRefundSerializer, PaymentSerializer, SchoolBillingSettingsSerializer
from .services import generate_fee_schedule_invoices, issue_invoice, post_credit_note, record_payment_refund


class BillingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    school_lookup_kwarg = "school_pk"
    write_roles = {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN, SchoolMembership.Role.ACCOUNTANT, SchoolMembership.Role.BURSAR}

    def get_school(self):
        if not hasattr(self, "_school"):
            self._school = get_object_or_404(School.objects.filter(
                memberships__user=self.request.user, memberships__is_active=True, is_active=True
            ).distinct(), pk=self.kwargs[self.school_lookup_kwarg])
        return self._school

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "school": self.get_school()}

    def check_write_role(self):
        member = SchoolMembership.objects.filter(school=self.get_school(), user=self.request.user, is_active=True).first()
        if not member or member.role not in self.write_roles:
            raise PermissionDenied("Your school role does not permit this billing operation.")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_CREATED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Created {instance.__class__.__name__}")

    def perform_update(self, serializer):
        self.check_write_role()
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_UPDATED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Updated {instance.__class__.__name__}")

    def perform_destroy(self, instance):
        self.check_write_role()
        instance.delete()


class FeeItemViewSet(BillingViewSet):
    serializer_class = FeeItemSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return FeeItem.objects.filter(school=self.get_school()).select_related("income_account")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action="FEE_ITEM_CREATED", entity_type="FeeItem", entity_id=instance.pk, summary=f"Created fee item {instance.code}")


class FeeScheduleViewSet(BillingViewSet):
    serializer_class = FeeScheduleSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return FeeSchedule.objects.filter(school=self.get_school()).select_related(
            "academic_year", "classroom", "period"
        ).prefetch_related("lines__fee_item", "generated_invoices")

    def perform_create(self, serializer):
        self.check_write_role()
        schedule = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user, action="FEE_SCHEDULE_CREATED",
            entity_type="FeeSchedule", entity_id=schedule.pk,
            summary=f"Created {schedule.term_name} fee schedule for {schedule.classroom}",
            metadata={"academic_year_id": schedule.academic_year_id, "period_id": schedule.period_id},
        )

    @action(detail=True, methods=["post"], url_path="generate-invoices")
    def generate_invoices(self, request, school_pk=None, pk=None):
        self.check_write_role()
        schedule = self.get_object()
        try:
            result = generate_fee_schedule_invoices(schedule.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(result, status=status.HTTP_200_OK)


class BillingSettingsViewSet(BillingViewSet):
    serializer_class = SchoolBillingSettingsSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        return SchoolBillingSettings.objects.filter(school=self.get_school())

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action="BILLING_SETTINGS_CREATED", entity_type="SchoolBillingSettings", entity_id=instance.pk, summary="Created billing account mappings")

    def update(self, request, *args, **kwargs):
        self.check_write_role()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.check_write_role()
        return super().partial_update(request, *args, **kwargs)


class InvoiceViewSet(BillingViewSet):
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Invoice.objects.filter(school=self.get_school()).select_related("student", "academic_year", "period").prefetch_related("lines__fee_item", "allocations")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action="INVOICE_DRAFT_CREATED", entity_type="Invoice", entity_id=instance.pk, summary=f"Created draft invoice {instance.invoice_number}", metadata={"student_id": instance.student_id, "amount": str(instance.total_amount)})

    @action(detail=True, methods=["post"])
    def issue(self, request, school_pk=None, pk=None):
        self.check_write_role()
        invoice = self.get_object()
        try:
            invoice = issue_invoice(invoice.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(invoice).data, status=status.HTTP_200_OK)


class PaymentViewSet(BillingViewSet):
    serializer_class = PaymentSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Payment.objects.filter(school=self.get_school()).select_related("student", "journal_entry").prefetch_related("allocations")

    def perform_create(self, serializer):
        self.check_write_role()
        try:
            serializer.save()
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        except IntegrityError as exc:
            raise ValidationError("This receipt or external payment reference has already been recorded.") from exc

    @action(detail=True, methods=["post"], url_path="refunds")
    def refund(self, request, school_pk=None, pk=None):
        self.check_write_role()
        payment = self.get_object()
        serializer = PaymentRefundInputSerializer(data=request.data, context={"school": self.get_school()})
        serializer.is_valid(raise_exception=True)
        try:
            refund = record_payment_refund(payment.pk, request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        except IntegrityError as exc:
            raise ValidationError("The refund could not be recorded because of a duplicate or conflicting ledger reference.") from exc
        return Response(PaymentRefundSerializer(refund).data, status=status.HTTP_201_CREATED)

class CreditNoteViewSet(BillingViewSet):
    serializer_class = CreditNoteSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return CreditNote.objects.filter(school=self.get_school()).select_related(
            "invoice", "period", "journal_entry", "created_by"
        ).prefetch_related("lines__invoice_line__fee_item")

    def perform_create(self, serializer):
        self.check_write_role()
        note = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user, action="CREDIT_NOTE_CREATED",
            entity_type="CreditNote", entity_id=note.pk,
            summary=f"Created draft credit note {note.credit_note_number}",
            metadata={"invoice_id": note.invoice_id, "amount": str(note.amount)},
        )

    @action(detail=True, methods=["post"])
    def post(self, request, school_pk=None, pk=None):
        self.check_write_role()
        note = self.get_object()
        try:
            note = post_credit_note(note.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(note).data, status=status.HTTP_200_OK)


