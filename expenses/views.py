from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import Expense, ExpenseBudget, ExpenseCategory, Supplier, SupplierBill
from .serializers import ExpenseBudgetSerializer, ExpenseCategorySerializer, ExpenseSerializer, SupplierSerializer, SupplierBillSerializer, RecordSupplierBillPaymentSerializer
from .services import post_expense
from .payables import approve_supplier_bill, post_supplier_bill, record_supplier_bill_payment, submit_supplier_bill


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
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action="SUPPLIER_CREATED", entity_type="Supplier", entity_id=instance.pk, summary="Created supplier record")


class ExpenseCategoryViewSet(SchoolExpensesViewSet):
    serializer_class = ExpenseCategorySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(school=self.get_school()).select_related("expense_account")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action="EXPENSE_CATEGORY_CREATED", entity_type="ExpenseCategory", entity_id=instance.pk, summary="Created expense category")


class ExpenseViewSet(SchoolExpensesViewSet):
    serializer_class = ExpenseSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Expense.objects.filter(school=self.get_school()).select_related("supplier", "category", "period", "journal_entry")

    def perform_update(self, serializer):
        self.check_write_role()
        if serializer.instance.status != Expense.Status.DRAFT:
            raise PermissionDenied("Posted expenses are immutable.")
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action="EXPENSE_DRAFT_UPDATED", entity_type="Expense", entity_id=instance.pk, summary=f"Updated draft expense {instance.expense_number}")

    @action(detail=True, methods=["post"])
    def post_expense(self, request, school_pk=None, pk=None):
        self.check_write_role()
        expense = self.get_object()
        try:
            expense = post_expense(expense.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(expense).data, status=status.HTTP_200_OK)

class SupplierBillViewSet(SchoolExpensesViewSet):
    serializer_class = SupplierBillSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return SupplierBill.objects.filter(school=self.get_school()).select_related(
            "supplier", "category", "period", "payable_account", "created_by",
            "submitted_by", "approved_by", "journal_entry",
        ).prefetch_related("payments")

    def perform_create(self, serializer):
        self.check_write_role()
        bill = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="SUPPLIER_BILL_CREATED", entity_type="SupplierBill",
            entity_id=bill.pk, summary=f"Created draft supplier bill {bill.bill_number}",
        )

    def perform_update(self, serializer):
        self.check_write_role()
        if serializer.instance.status != SupplierBill.Status.DRAFT:
            raise PermissionDenied("Only draft supplier bills can be edited.")
        bill = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="SUPPLIER_BILL_DRAFT_UPDATED", entity_type="SupplierBill",
            entity_id=bill.pk, summary=f"Updated draft supplier bill {bill.bill_number}",
        )

    def _run_bill_action(self, request, action_function):
        self.check_write_role()
        bill = self.get_object()
        try:
            bill = action_function(bill.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(bill).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def submit(self, request, school_pk=None, pk=None):
        return self._run_bill_action(request, submit_supplier_bill)

    @action(detail=True, methods=["post"])
    def approve(self, request, school_pk=None, pk=None):
        member = SchoolMembership.objects.filter(
            school=self.get_school(), user=request.user, is_active=True
        ).first()
        if not member or member.role not in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
            raise PermissionDenied("Only the school owner or administrator can approve supplier bills.")
        return self._run_bill_action(request, approve_supplier_bill)

    @action(detail=True, methods=["post"])
    def post_bill(self, request, school_pk=None, pk=None):
        return self._run_bill_action(request, post_supplier_bill)

    @action(detail=True, methods=["post"], url_path="payments")
    def record_payment(self, request, school_pk=None, pk=None):
        self.check_write_role()
        bill = self.get_object()
        serializer = RecordSupplierBillPaymentSerializer(
            data=request.data, context={"school": self.get_school()}
        )
        serializer.is_valid(raise_exception=True)
        try:
            record_supplier_bill_payment(
                bill.pk, request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        bill.refresh_from_db()
        return Response(self.get_serializer(bill).data, status=status.HTTP_200_OK)



class ExpenseBudgetViewSet(SchoolExpensesViewSet):
    serializer_class = ExpenseBudgetSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = ExpenseBudget.objects.filter(school=self.get_school()).select_related(
            "period", "category", "created_by"
        )
        period_id = self.request.query_params.get("period")
        if period_id:
            queryset = queryset.filter(period_id=period_id)
        return queryset

    def perform_create(self, serializer):
        self.check_write_role()
        budget = serializer.save(school=self.get_school(), created_by=self.request.user)
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="EXPENSE_BUDGET_CREATED", entity_type="ExpenseBudget",
            entity_id=budget.pk, summary=f"Created budget for {budget.category.name} in {budget.period.name}",
        )

    def perform_update(self, serializer):
        self.check_write_role()
        budget = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="EXPENSE_BUDGET_UPDATED", entity_type="ExpenseBudget",
            entity_id=budget.pk, summary=f"Updated budget for {budget.category.name} in {budget.period.name}",
        )
