from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from .models import Account, FinancialPeriod, JournalEntry
from .serializers import AccountSerializer, FinancialPeriodSerializer, JournalEntrySerializer


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
        serializer.save(school=self.get_school())

    def perform_update(self, serializer):
        self.check_write_role()
        serializer.save()

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
        serializer.save()


class FinancialPeriodViewSet(SchoolLedgerViewSet):
    serializer_class = FinancialPeriodSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return FinancialPeriod.objects.filter(school=self.get_school()).order_by("-starts_on")

    def perform_update(self, serializer):
        self.check_write_role()
        if serializer.instance.is_locked:
            raise PermissionDenied("A locked financial period cannot be edited.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def lock_period(self, request, school_pk=None, pk=None):
        self.check_write_role()
        period = self.get_object()
        period.is_locked = True
        period.save(update_fields=["is_locked"])
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
        serializer.save()

    @action(detail=True, methods=["post"])
    def post_entry(self, request, school_pk=None, pk=None):
        self.check_write_role()
        entry = self.get_object()
        try:
            entry.post()
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(entry).data, status=status.HTTP_200_OK)
