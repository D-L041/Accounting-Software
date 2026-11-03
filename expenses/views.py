from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import Expense, ExpenseBudget, ExpenseCategory, Supplier, SupplierBill, PurchaseOrder, PurchaseOrderApproval, ProcurementApprovalRule
from .serializers import ExpenseBudgetSerializer, ExpenseCategorySerializer, ExpenseSerializer, SupplierSerializer, SupplierBillSerializer, RecordSupplierBillPaymentSerializer, PurchaseOrderSerializer, ProcurementApprovalRuleSerializer
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


class ProcurementApprovalRuleViewSet(SchoolExpensesViewSet):
    serializer_class = ProcurementApprovalRuleSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return ProcurementApprovalRule.objects.filter(school=self.get_school())

    def check_admin(self):
        member = SchoolMembership.objects.filter(school=self.get_school(), user=self.request.user, is_active=True).first()
        if not member or member.role not in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
            raise PermissionDenied("Only the school owner or administrator can configure procurement approval rules.")

    def perform_create(self, serializer):
        self.check_admin()
        serializer.save(school=self.get_school())

    def perform_update(self, serializer):
        self.check_admin()
        serializer.save()

    def perform_destroy(self, instance):
        self.check_admin()
        instance.delete()


class PurchaseOrderViewSet(SchoolExpensesViewSet):
    serializer_class = PurchaseOrderSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return PurchaseOrder.objects.filter(school=self.get_school()).select_related(
            "supplier", "period", "created_by"
        ).prefetch_related("lines", "approvals__approved_by")

    def perform_create(self, serializer):
        self.check_write_role()
        order = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user,
                     action="PURCHASE_ORDER_CREATED", entity_type="PurchaseOrder",
                     entity_id=order.pk, summary=f"Created draft purchase order {order.order_number}")

    def perform_update(self, serializer):
        self.check_write_role()
        if serializer.instance.status != PurchaseOrder.Status.DRAFT:
            raise PermissionDenied("Only draft purchase orders can be edited.")
        order = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user,
                     action="PURCHASE_ORDER_UPDATED", entity_type="PurchaseOrder",
                     entity_id=order.pk, summary=f"Updated draft purchase order {order.order_number}")

    @action(detail=True, methods=["post"])
    def submit(self, request, school_pk=None, pk=None):
        self.check_write_role()
        from django.db import transaction
        from django.utils import timezone
        order = self.get_object()
        if order.status != PurchaseOrder.Status.DRAFT or not order.lines.exists():
            raise ValidationError("Only a non-empty draft purchase order can be submitted.")
        with transaction.atomic():
            rules = list(ProcurementApprovalRule.objects.filter(
                school=self.get_school(), is_active=True, min_amount__lte=order.total_amount
            ).order_by("step_number", "-min_amount"))
            steps = {}
            for rule in rules:
                steps.setdefault(rule.step_number, rule.approver_role)
            if not steps:
                steps = {1: "OWNER"}
            expected_steps = list(range(1, max(steps) + 1))
            if sorted(steps) != expected_steps:
                raise ValidationError(
                    "Active approval rules for this order must include every stage from 1 through the final stage. "
                    "Ask a school owner or administrator to correct the approval configuration."
                )
            for step, role in sorted(steps.items()):
                PurchaseOrderApproval.objects.create(
                    purchase_order=order, step_number=step, approver_role=role
                )
            order.status = PurchaseOrder.Status.SUBMITTED
            order.submitted_at = timezone.now()
            order.save(update_fields=["status", "submitted_at"])
            record_event(school=self.get_school(), actor=request.user,
                         action="PURCHASE_ORDER_SUBMITTED", entity_type="PurchaseOrder",
                         entity_id=order.pk, summary=f"Submitted {order.order_number} for {len(steps)} approval step(s)")
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, school_pk=None, pk=None):
        self.check_write_role()
        from django.db import transaction
        from django.utils import timezone
        order = self.get_object()
        if order.status != PurchaseOrder.Status.SUBMITTED:
            raise ValidationError("Only submitted purchase orders can be approved.")
        if order.created_by_id == request.user.id:
            raise PermissionDenied("The person who created a purchase order cannot approve it.")
        with transaction.atomic():
            approval = order.approvals.filter(approved_at__isnull=True).order_by("step_number").first()
            if not approval:
                raise ValidationError("No outstanding approval step exists.")
            member = SchoolMembership.objects.filter(
                school=self.get_school(), user=request.user, is_active=True
            ).first()
            if not member or member.role != approval.approver_role:
                raise PermissionDenied(f"This approval step requires the {approval.approver_role} role.")
            approval.approved_by = request.user
            approval.approved_at = timezone.now()
            approval.save(update_fields=["approved_by", "approved_at"])
            if not order.approvals.filter(approved_at__isnull=True).exists():
                order.status = PurchaseOrder.Status.APPROVED
                order.save(update_fields=["status"])
            record_event(school=self.get_school(), actor=request.user,
                         action="PURCHASE_ORDER_STEP_APPROVED", entity_type="PurchaseOrder",
                         entity_id=order.pk, summary=f"Approved step {approval.step_number} of {order.order_number}")
        order.refresh_from_db()
        return Response(self.get_serializer(order).data)
