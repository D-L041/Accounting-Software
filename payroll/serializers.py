from rest_framework import serializers

from ledger.models import Account, FinancialPeriod
from .models import Employee, PayrollLine, PayrollRule, PayrollRun, PayrollSettings, PayrollTaxBand


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id", "employee_number", "first_name", "last_name", "full_name",
            "job_title", "basic_salary", "regular_cash_allowances", "monthly_other_deductions", "is_resident", "hire_date",
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "full_name", "created_at"]

    def validate(self, attrs):
        salary = attrs.get("basic_salary", getattr(self.instance, "basic_salary", 0))
        if salary < 0:
            raise serializers.ValidationError({"basic_salary": "Salary cannot be negative."})
        return attrs


class PayrollSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollSettings
        fields = [
            "id", "salary_expense_account", "net_payable_account",
            "paye_payable_account", "nssf_payable_account",
            "shif_payable_account", "housing_levy_payable_account", "other_deductions_payable_account",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        school = self.context["school"]
        expected = {
            "salary_expense_account": Account.Category.EXPENSE,
            "net_payable_account": Account.Category.LIABILITY,
            "paye_payable_account": Account.Category.LIABILITY,
            "nssf_payable_account": Account.Category.LIABILITY,
            "shif_payable_account": Account.Category.LIABILITY,
            "housing_levy_payable_account": Account.Category.LIABILITY,
            "other_deductions_payable_account": Account.Category.LIABILITY,
            "nita_payable_account": Account.Category.LIABILITY,
        }
        for field, category in expected.items():
            account = attrs.get(field, getattr(self.instance, field, None))
            if account and (account.school_id != school.id or account.category != category):
                raise serializers.ValidationError({field: f"Select a {category.lower()} account belonging to this school."})
        return attrs


class PayrollLineSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_number = serializers.CharField(source="employee.employee_number", read_only=True)

    class Meta:
        model = PayrollLine
        fields = [
            "id", "employee", "employee_name", "employee_number", "basic_salary",
            "other_earnings", "gross_pay", "taxable_pay", "paye",
            "nssf_employee", "shif_employee", "housing_levy_employee",
            "other_deductions", "net_pay", "nssf_employer", "housing_levy_employer", "nita_levy_employer",
        ]


class PayrollRunInputSerializer(serializers.Serializer):
    period = serializers.PrimaryKeyRelatedField(queryset=FinancialPeriod.objects.all())
    payroll_month = serializers.DateField()
    pay_date = serializers.DateField()

    def validate_period(self, value):
        if value.school_id != self.context["school"].id:
            raise serializers.ValidationError("Financial period must belong to this school.")
        return value


class PayrollRunSerializer(serializers.ModelSerializer):
    lines = PayrollLineSerializer(many=True, read_only=True)
    gross_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    net_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    employer_contributions_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = PayrollRun
        fields = [
            "id", "period", "payroll_month", "pay_date", "status",
            "journal_entry", "created_by", "created_at", "gross_total",
            "net_total", "employer_contributions_total", "employee_count", "lines",
        ]
        read_only_fields = fields

    def get_employee_count(self, obj):
        return obj.lines.count()

class PayrollRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRule
        fields = [
            "id", "code", "effective_from", "effective_to", "employee_rate",
            "employer_rate", "ceiling", "minimum_employee", "fixed_employee", "fixed_employer",
            "deductible_for_paye", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PayrollTaxBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollTaxBand
        fields = ["id", "effective_from", "effective_to", "lower_bound", "upper_bound", "rate"]
        read_only_fields = ["id"]
