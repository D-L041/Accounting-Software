import csv

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import School, SchoolMembership
from auditlog.services import record_event
from .models import Employee, PayrollRule, PayrollRun, PayrollSettings, PayrollTaxBand
from .serializers import EmployeeSerializer, PayrollRuleSerializer, PayrollRunInputSerializer, PayrollRunSerializer, PayrollSettingsSerializer, PayrollTaxBandSerializer
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

    def check_admin_role(self):
        member = SchoolMembership.objects.filter(
            school=self.get_school(), user=self.request.user, is_active=True
        ).first()
        if not member or member.role not in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
            raise PermissionDenied("Only the school owner or administrator can change statutory payroll rules.")

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
        sensitive_fields = {
            "monthly_insurance_premiums", "monthly_mortgage_interest",
            "monthly_post_retirement_medical", "monthly_additional_pension",
            "tax_claims_reference", "tax_claims_verified",
            "tax_exemption_certificate_ref", "tax_exemption_valid_from",
            "tax_exemption_valid_to", "tax_exemption_verified",
        }
        if any(field in serializer.validated_data for field in sensitive_fields):
            self.check_admin_role()
        employee = serializer.save(school=self.get_school())
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="EMPLOYEE_CREATED", entity_type="Employee", entity_id=employee.pk,
            summary=f"Created employee {employee.employee_number}",
        )

    def perform_update(self, serializer):
        self.check_write_role()
        changes = serializer.validated_data
        sensitive_fields = {
            "monthly_insurance_premiums", "monthly_mortgage_interest",
            "monthly_post_retirement_medical", "monthly_additional_pension",
            "tax_claims_reference", "tax_claims_verified",
            "tax_exemption_certificate_ref", "tax_exemption_valid_from",
            "tax_exemption_valid_to", "tax_exemption_verified",
        }
        if any(field in changes for field in sensitive_fields):
            self.check_admin_role()
        claim_fields = {
            "monthly_insurance_premiums", "monthly_mortgage_interest",
            "monthly_post_retirement_medical", "monthly_additional_pension",
            "tax_claims_reference",
        }
        exemption_fields = {
            "tax_exemption_certificate_ref", "tax_exemption_valid_from", "tax_exemption_valid_to",
        }
        save_kwargs = {}
        if any(field in changes and changes[field] != getattr(serializer.instance, field) for field in claim_fields):
            if changes.get("tax_claims_verified") is not True:
                save_kwargs["tax_claims_verified"] = False
        if any(field in changes and changes[field] != getattr(serializer.instance, field) for field in exemption_fields):
            if changes.get("tax_exemption_verified") is not True:
                save_kwargs["tax_exemption_verified"] = False
        employee = serializer.save(**save_kwargs)
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

    @action(detail=True, methods=["get"], url_path="statutory-export")
    def statutory_export(self, request, school_pk=None, pk=None):
        run = get_object_or_404(self.get_queryset(), pk=pk)
        schedule = request.query_params.get("schedule", "REGISTER").upper()
        schedules = {
            "REGISTER": (
                ["Employee number", "Employee name", "Payroll month", "Status", "Gross pay", "Taxable pay",
                 "PAYE", "NSSF employee", "NSSF employer", "SHIF", "Housing levy employee",
                 "Housing levy employer", "NITA employer", "Insurance premium claimed", "Insurance relief",
                 "Mortgage interest deduction", "Post-retirement medical deduction", "Additional pension employee",
                 "Additional pension allowable", "Tax-exempt income", "Other deductions", "Net pay"],
                lambda line: [
                    line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                    run.status, line.gross_pay, line.taxable_pay, line.paye, line.nssf_employee,
                    line.nssf_employer, line.shif_employee, line.housing_levy_employee,
                    line.housing_levy_employer, line.nita_levy_employer, line.insurance_premium_claimed,
                    line.insurance_relief, line.mortgage_interest_deduction,
                    line.post_retirement_medical_deduction, line.additional_pension_employee,
                    line.additional_pension_allowable, line.tax_exempt_income, line.other_deductions, line.net_pay,
                ],
            ),
            "PAYE": (
                ["Employee number (KRA PIN capture pending)", "Employee name", "Payroll month", "Gross pay",
                 "Taxable pay", "PAYE", "Insurance relief", "Mortgage interest deduction",
                 "Post-retirement medical deduction", "Allowable pension deduction", "Tax-exempt income"],
                lambda line: [line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                              line.gross_pay, line.taxable_pay, line.paye, line.insurance_relief,
                              line.mortgage_interest_deduction, line.post_retirement_medical_deduction,
                              line.additional_pension_allowable, line.tax_exempt_income],
            ),
            "NSSF": (
                ["Employee number", "Employee name", "Payroll month", "Employee NSSF", "Employer NSSF", "Total NSSF"],
                lambda line: [line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                              line.nssf_employee, line.nssf_employer, line.nssf_employee + line.nssf_employer],
            ),
            "SHIF": (
                ["Employee number", "Employee name", "Payroll month", "Gross pay", "SHIF contribution"],
                lambda line: [line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                              line.gross_pay, line.shif_employee],
            ),
            "AHL": (
                ["Employee number", "Employee name", "Payroll month", "Gross pay", "Employee levy", "Employer levy", "Total levy"],
                lambda line: [line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                              line.gross_pay, line.housing_levy_employee, line.housing_levy_employer,
                              line.housing_levy_employee + line.housing_levy_employer],
            ),
            "PENSION": (
                ["Employee number", "Employee name", "Payroll month", "Employee additional pension", "Allowable PAYE pension deduction"],
                lambda line: [line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                              line.additional_pension_employee, line.additional_pension_allowable],
            ),
            "NITA": (
                ["Employee number", "Employee name", "Payroll month", "Employer NITA levy"],
                lambda line: [line.employee.employee_number, line.employee.full_name, run.payroll_month.isoformat(),
                              line.nita_levy_employer],
            ),
        }
        if schedule not in schedules:
            raise ValidationError({"schedule": "Choose REGISTER, PAYE, NSSF, SHIF, AHL, PENSION or NITA."})
        if schedule != "REGISTER" and run.status != PayrollRun.Status.POSTED:
            raise ValidationError("Statutory schedules are available only after payroll has been posted.")
        headers, row_values = schedules[schedule]
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="precious-payroll-{run.payroll_month:%Y-%m}-{schedule.lower()}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(headers)
        for line in run.lines.select_related("employee").order_by("employee__employee_number"):
            values = row_values(line)
            # Prevent spreadsheet formula execution from employee-controlled text fields.
            safe_values = [
                "'" + value if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\\t", "\\r") else value
                for value in values
            ]
            writer.writerow(safe_values)
        record_event(
            school=run.school, actor=request.user, action="PAYROLL_EXPORT_DOWNLOADED",
            entity_type="PayrollRun", entity_id=run.pk,
            summary=f"Downloaded {schedule} payroll export for {run.payroll_month:%B %Y}",
            metadata={"schedule": schedule, "payroll_status": run.status},
        )
        return response

    @action(detail=True, methods=["post"])
    def post(self, request, school_pk=None, pk=None):
        self.check_write_role()
        run = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            run = post_payroll_run(run.pk, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return Response(self.get_serializer(run).data, status=status.HTTP_200_OK)

class PayrollRuleViewSet(SchoolPayrollViewSet, viewsets.ModelViewSet):
    serializer_class = PayrollRuleSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return PayrollRule.objects.filter(Q(school=self.get_school()) | Q(school__isnull=True))

    def perform_create(self, serializer):
        self.check_admin_role()
        rule = serializer.save(school=self.get_school())
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="PAYROLL_RULE_CREATED", entity_type="PayrollRule", entity_id=rule.pk,
            summary=f"Created effective-dated {rule.code} payroll rule",
            metadata={"effective_from": rule.effective_from.isoformat(), "effective_to": rule.effective_to.isoformat() if rule.effective_to else None},
        )

    def perform_update(self, serializer):
        self.check_admin_role()
        if serializer.instance.school_id != self.get_school().id:
            raise PermissionDenied("Global statutory rules cannot be edited by a school.")
        rule = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="PAYROLL_RULE_UPDATED", entity_type="PayrollRule", entity_id=rule.pk,
            summary=f"Updated effective-dated {rule.code} payroll rule",
        )


class PayrollTaxBandViewSet(SchoolPayrollViewSet, viewsets.ModelViewSet):
    serializer_class = PayrollTaxBandSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return PayrollTaxBand.objects.filter(Q(school=self.get_school()) | Q(school__isnull=True))

    def perform_create(self, serializer):
        self.check_admin_role()
        band = serializer.save(school=self.get_school())
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="PAYROLL_TAX_BAND_CREATED", entity_type="PayrollTaxBand", entity_id=band.pk,
            summary="Created effective-dated PAYE tax band",
        )

    def perform_update(self, serializer):
        self.check_admin_role()
        if serializer.instance.school_id != self.get_school().id:
            raise PermissionDenied("Global PAYE tax bands cannot be edited by a school.")
        band = serializer.save()
        record_event(
            school=self.get_school(), actor=self.request.user,
            action="PAYROLL_TAX_BAND_UPDATED", entity_type="PayrollTaxBand", entity_id=band.pk,
            summary="Updated effective-dated PAYE tax band",
        )

