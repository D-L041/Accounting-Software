from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import Account, BankStatement, BankStatementLine, FinancialPeriod, JournalEntry, JournalLine
from .serializers import AccountSerializer, BankStatementSerializer, FinancialPeriodSerializer, JournalEntrySerializer


class SchoolLedgerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    school_lookup_kwarg = "school_pk"
    write_roles = {
        SchoolMembership.Role.OWNER,
        SchoolMembership.Role.ADMIN,
        SchoolMembership.Role.ACCOUNTANT,
    }

    def get_school(self):
        if not hasattr(self, "_school"):
            self._school = get_object_or_404(
                School.objects.filter(
                    memberships__user=self.request.user,
                    memberships__is_active=True,
                    is_active=True,
                ).distinct(),
                pk=self.kwargs[self.school_lookup_kwarg],
            )
        return self._school

    def check_write_role(self):
        membership = SchoolMembership.objects.filter(
            school=self.get_school(), user=self.request.user, is_active=True
        ).first()
        if not membership or membership.role not in self.write_roles:
            raise PermissionDenied("Your school role does not permit this accounting operation.")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "school": self.get_school()}

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


class AccountViewSet(SchoolLedgerViewSet):
    serializer_class = AccountSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Account.objects.filter(school=self.get_school()).order_by("code")

    def perform_update(self, serializer):
        self.check_write_role()
        account = serializer.instance
        used_in_posted_journal = account.journalline_set.filter(entry__posted=True).exists()
        changed_fields = set(serializer.validated_data) - {"is_active"}
        if used_in_posted_journal and changed_fields:
            raise PermissionDenied("An account used in posted journals cannot have its code, name or category changed.")
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action="ACCOUNT_UPDATED", entity_type="Account", entity_id=instance.pk, summary=f"Updated ledger account {instance.code}")


class FinancialPeriodViewSet(SchoolLedgerViewSet):
    serializer_class = FinancialPeriodSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return FinancialPeriod.objects.filter(school=self.get_school()).order_by("-starts_on")

    def perform_update(self, serializer):
        self.check_write_role()
        if serializer.instance.is_locked:
            raise PermissionDenied("A locked financial period cannot be edited.")
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action="FINANCIAL_PERIOD_UPDATED", entity_type="FinancialPeriod", entity_id=instance.pk, summary=f"Updated financial period {instance.name}")

    @action(detail=True, methods=["post"])
    def lock_period(self, request, school_pk=None, pk=None):
        self.check_write_role()
        period = self.get_object()
        period.is_locked = True
        period.save(update_fields=["is_locked"])
        record_event(
            school=period.school, actor=request.user, action="PERIOD_LOCKED",
            entity_type="FinancialPeriod", entity_id=period.pk,
            summary=f"Locked financial period {period.name}",
            metadata={"starts_on": period.starts_on.isoformat(), "ends_on": period.ends_on.isoformat()},
        )
        return Response(self.get_serializer(period).data, status=status.HTTP_200_OK)


class JournalEntryViewSet(SchoolLedgerViewSet):
    serializer_class = JournalEntrySerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return JournalEntry.objects.filter(school=self.get_school()).select_related(
            "period", "created_by"
        ).prefetch_related("lines__account").order_by("-entry_date", "-id")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action="JOURNAL_DRAFT_CREATED", entity_type="JournalEntry", entity_id=instance.pk, summary=f"Created draft journal {instance.reference}")

    @action(detail=True, methods=["post"])
    def post_entry(self, request, school_pk=None, pk=None):
        self.check_write_role()
        entry = self.get_object()
        try:
            entry.post(actor=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(entry).data, status=status.HTTP_200_OK)

class BankStatementViewSet(SchoolLedgerViewSet):
    serializer_class = BankStatementSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return BankStatement.objects.filter(school=self.get_school()).select_related(
            "account", "period", "uploaded_by"
        ).prefetch_related("lines__matched_journal_line__entry").order_by("-statement_end", "-id")

    def perform_create(self, serializer):
        self.check_write_role()
        statement = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user, action="BANK_STATEMENT_CREATED",
            entity_type="BankStatement", entity_id=statement.pk,
            summary=f"Imported bank statement ending {statement.statement_end}",
            metadata={"account_id": statement.account_id, "period_id": statement.period_id,
                      "line_count": statement.lines.count()},
        )

    @action(detail=True, methods=["post"], url_path="match-line")
    def match_line(self, request, school_pk=None, pk=None):
        self.check_write_role()
        statement = self.get_object()
        if statement.status != BankStatement.Status.DRAFT:
            raise PermissionDenied("A reconciled bank statement cannot be changed.")
        try:
            statement_line = statement.lines.get(pk=request.data.get("statement_line_id"))
            journal_line = JournalLine.objects.select_related("entry", "account").get(
                pk=request.data.get("journal_line_id"),
                entry__school=self.get_school(),
                entry__period=statement.period,
                entry__posted=True,
                account=statement.account,
            )
            statement_line.matched_journal_line = journal_line
            statement_line.full_clean()
            statement_line.save(update_fields=["matched_journal_line"])
        except (BankStatementLine.DoesNotExist, JournalLine.DoesNotExist):
            raise ValidationError("Select a statement line and a posted ledger line belonging to this school, period and bank account.")
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        record_event(
            school=self.get_school(), actor=request.user, action="BANK_STATEMENT_LINE_MATCHED",
            entity_type="BankStatementLine", entity_id=statement_line.pk,
            summary=f"Matched statement line to journal {journal_line.entry.reference}",
            metadata={"statement_id": statement.pk, "journal_line_id": journal_line.pk},
        )
        return Response(self.get_serializer(statement).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reconcile(self, request, school_pk=None, pk=None):
        self.check_write_role()
        statement = self.get_object()
        try:
            statement.reconcile(actor=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(statement).data, status=status.HTTP_200_OK)

