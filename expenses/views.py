from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import Expense, ExpenseCategory, Supplier
from .serializers import ExpenseCategorySerializer, ExpenseSerializer, SupplierSerializer
from .services import post_expense


class SchoolExpensesViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    write_roles = {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN, SchoolMembership.Role.ACCOUNTANT, SchoolMembership.Role.BURSAR}

    def get_school(self):
        if not hasattr(self, "_school"):
            self._school = get_object_or_404(School.objects.filter(
                memberships__user=self.request.user, memberships__is_active=True, is_active=True
            ).distinct(), pk=self.kwargs["school_pk"])
        return self._school

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "school": self.get_school()}

    def check_write_role(self):
        member = SchoolMembership.objects.filter(school=self.get_school(), user=self.request.user, is_active=True).first()
        if not member or member.role not in self.write_roles:
            raise PermissionDenied("Your school role does not permit this operation.")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_CREATED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Created {instance.__class__.__name__}")

    def perform_update(self, serializer):
        self.check_write_role()
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_UPDATED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Updated {instance.__class__.__name__}")


class SupplierViewSet(SchoolExpensesViewSet):
    serializer_class = SupplierSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Supplier.objects.filter(school=self.get_school())

    def perform_create(self, serializer):
        self.check_write_role()
        serializer.save(school=self.get_school())


class ExpenseCategoryViewSet(SchoolExpensesViewSet):
    serializer_class = ExpenseCategorySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(school=self.get_school()).select_related("expense_account")

    def perform_create(self, serializer):
        self.check_write_role()
        serializer.save(school=self.get_school())


class ExpenseViewSet(SchoolExpensesViewSet):
    serializer_class = ExpenseSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Expense.objects.filter(school=self.get_school()).select_related("supplier", "category", "period", "journal_entry")

    def perform_update(self, serializer):
        self.check_write_role()
        if serializer.instance.status != Expense.Status.DRAFT:
            raise PermissionDenied("Posted expenses are immutable.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def post_expense(self, request, school_pk=None, pk=None):
        self.check_write_role()
        expense = self.get_object()
        try:
            expense = post_expense(expense.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(expense).data, status=status.HTTP_200_OK)
