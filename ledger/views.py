from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
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


class JournalEntryViewSet(SchoolLedgerViewSet):
    serializer_class = JournalEntrySerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return JournalEntry.objects.filter(school=self.get_school()).select_related(
            "period", "created_by"
        ).prefetch_related("lines__account").order_by("-entry_date", "-id")

    @action(detail=True, methods=["post"])
    def post_entry(self, request, school_pk=None, pk=None):
        self.check_write_role()
        entry = self.get_object()
        entry.post()
        return Response(self.get_serializer(entry).data, status=status.HTTP_200_OK)
