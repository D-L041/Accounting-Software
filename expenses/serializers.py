from rest_framework import serializers

from billing.models import Payment
from ledger.models import Account, FinancialPeriod
from .models import Expense, ExpenseCategory, Supplier, SupplierBill, SupplierBillPayment


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "email", "tax_pin", "address", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    expense_account_name = serializers.CharField(source="expense_account.name", read_only=True)

    class Meta:
        model = ExpenseCategory
        fields = ["id", "code", "name", "expense_account", "expense_account_name", "is_active"]
        read_only_fields = ["id", "expense_account_name"]

    def validate_expense_account(self, value):
        if value.school_id != self.context["school"].id or value.category != Account.Category.EXPENSE:
            raise serializers.ValidationError("Choose an expense account belonging to this school.")
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "supplier", "supplier_name", "category", "category_name", "period", "period_name", "expense_number", "expense_date", "description", "amount", "payment_method", "reference", "status", "journal_entry", "created_at"]
        read_only_fields = ["id", "expense_number", "status", "journal_entry", "created_at", "supplier_name", "category_name", "period_name"]

    def validate(self, attrs):
        school = self.context["school"]
        for field in ("supplier", "category", "period"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value and value.school_id != school.id:
                raise serializers.ValidationError({field: f"{field.title()} must belong to this school."})
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Expense amount must be greater than zero."})
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        from django.db.models import Max
        from .models import Expense
        school = validated_data.pop("school", self.context["school"])
        with transaction.atomic():
            from accounts.models import School
            School.objects.select_for_update().get(pk=school.pk)
            last = Expense.objects.filter(school=school).order_by("-id").first()
            sequence = 1
            if last:
                try:
                    sequence = int(last.expense_number.rsplit("-", 1)[1]) + 1
                except (ValueError, IndexError):
                    raise serializers.ValidationError("The last expense number is invalid; contact an administrator.")
            number = f"EXP-{sequence:06d}"
            return Expense.objects.create(school=school, expense_number=number, **validated_data)

class SupplierBillPaymentSerializer(serializers.ModelSerializer):
    payment_account_name = serializers.CharField(source="payment_account.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = SupplierBillPayment
        fields = [
            "id", "payment_date", "amount", "payment_method", "payment_account",
            "payment_account_name", "period", "period_name", "reference",
            "journal_entry", "recorded_by", "created_at",
        ]
        read_only_fields = ["id", "journal_entry", "recorded_by", "created_at", "payment_account_name", "period_name"]


class SupplierBillSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    payable_account_name = serializers.CharField(source="payable_account.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    amount_paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    payments = SupplierBillPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierBill
        fields = [
            "id", "supplier", "supplier_name", "category", "category_name",
            "period", "period_name", "payable_account", "payable_account_name",
            "bill_number", "supplier_invoice_number", "bill_date", "due_date",
            "description", "amount", "amount_paid", "balance", "status",
            "created_by", "submitted_by", "submitted_at", "approved_by",
            "approved_at", "journal_entry", "payments", "created_at",
        ]
        read_only_fields = [
            "id", "bill_number", "status", "created_by", "submitted_by",
            "submitted_at", "approved_by", "approved_at", "journal_entry",
            "amount_paid", "balance", "payments", "created_at", "supplier_name",
            "category_name", "period_name", "payable_account_name",
        ]

    def validate(self, attrs):
        school = self.context["school"]
        for field in ("supplier", "category", "period", "payable_account"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value and value.school_id != school.id:
                raise serializers.ValidationError({field: f"{field.title()} must belong to this school."})
        payable = attrs.get("payable_account", getattr(self.instance, "payable_account", None))
        if payable and payable.category != Account.Category.LIABILITY:
            raise serializers.ValidationError({"payable_account": "Choose a liability account."})
        if self.instance and self.instance.status != SupplierBill.Status.DRAFT:
            raise serializers.ValidationError("Only draft supplier bills can be edited.")
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        from accounts.models import School
        school = self.context["school"]
        with transaction.atomic():
            School.objects.select_for_update().get(pk=school.pk)
            last = SupplierBill.objects.filter(school=school).order_by("-id").first()
            sequence = 1
            if last:
                try:
                    sequence = int(last.bill_number.rsplit("-", 1)[1]) + 1
                except (ValueError, IndexError):
                    raise serializers.ValidationError("The last supplier bill number is invalid; contact an administrator.")
            return SupplierBill.objects.create(
                school=school, bill_number=f"BILL-{sequence:06d}",
                created_by=self.context["request"].user, **validated_data,
            )

