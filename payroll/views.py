from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import Employee, PayrollRun, PayrollSettings
from .serializers import EmployeeSerializer, PayrollRunInputSerializer, PayrollRunSerializer, PayrollSettingsSerializer
from .services import create_payroll_run, post_payroll_run


class SchoolPayrollViewSet:
    permission_classes = [permissions.IsAuthenticated]
    write_roles = {
        SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN,
        SchoolMembership.Role.ACCOUNTANT, SchoolMembership.Role.BURSAR,
    }

    def get_school(self):
        if not hasattr(self, "_school"):
            self._school = get_object_or_404(
                School.objects.filter(
                    memberships__user=self.request.user,
                    memberships__is_active=True, is_active=True,
                ).distinct(),
                pk=self.kwargs["school_pk"],
            )
        return self._school

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "school": self.get_school()}

    def check_write_role(self):
        member = SchoolMembership.objects.filter(
            school=self.get_school(), user=self.request.user, is_active=True
        ).first()
        if not member or member.role not in self.write_roles:
            raise PermissionDenied("Your school role does not permit this payroll operation.")


class EmployeeViewSet(SchoolPayrollViewSet, viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Employee.objects.filter(school=self.get_school())

    def perform_create(self, serializer):
        self.check_write_role()
        employee = serializer.save(school=self.get_school())
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="EMPLOYEE_CREATED", entity_type="Employee", entity_id=employee.pk,
            summary=f"Created employee {employee.employee_number}",
        )

    def perform_update(self, serializer):
        self.check_write_role()
        employee = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="EMPLOYEE_UPDATED", entity_type="Employee", entity_id=employee.pk,
            summary=f"Updated employee {employee.employee_number}",
        )


class PayrollSettingsViewSet(SchoolPayrollViewSet, viewsets.ModelViewSet):
    serializer_class = PayrollSettingsSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return PayrollSettings.objects.filter(school=self.get_school())

    def create(self, request, *args, **kwargs):
        self.check_write_role()
        if self.get_queryset().exists():
            raise ValidationError("Payroll account mappings already exist; update the existing settings.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settings = serializer.save(school=self.get_school())
        record_event(
            school=self.get_school(), actor=request.user, action="PAYROLL_SETTINGS_CREATED",
            entity_type="PayrollSettings", entity_id=settings.pk,
            summary="Configured payroll ledger accounts",
        )
        return Response(self.get_serializer(settings).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        self.check_write_role()
        return super().partial_update(request, *args, **kwargs)


class PayrollRunViewSet(SchoolPayrollViewSet, viewsets.GenericViewSet):
    serializer_class = PayrollRunSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return PayrollRun.objects.filter(school=self.get_school()).select_related(
            "period", "journal_entry", "created_by"
        ).prefetch_related("lines__employee")

    def list(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, *args, **kwargs):
        run = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(self.get_serializer(run).data)

    def create(self, request, *args, **kwargs):
        self.check_write_role()
        serializer = PayrollRunInputSerializer(data=request.data, context={"school": self.get_school()})
        serializer.is_valid(raise_exception=True)
        try:
            run = create_payroll_run(
                school=self.get_school(), user=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        except IntegrityError as exc:
            raise ValidationError("A payroll run already exists for this school and month.") from exc
        return Response(PayrollRunSerializer(run, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def post(self, request, school_pk=None, pk=None):
        self.check_write_role()
        run = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            run = post_payroll_run(run.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(run).data, status=status.HTTP_200_OK)
