from decimal import Decimal

from rest_framework import serializers

from accounts.models import Student
from ledger.models import Account
from .models import FeeItem, Invoice, InvoiceLine, Payment, SchoolBillingSettings


class FeeItemSerializer(serializers.ModelSerializer):
    income_account_name = serializers.CharField(source="income_account.name", read_only=True)

    class Meta:
        model = FeeItem
        fields = ["id", "code", "name", "description", "income_account", "income_account_name", "is_active"]
        read_only_fields = ["id", "income_account_name"]

    def validate_income_account(self, value):
        if value.school_id != self.context["school"].id or value.category != Account.Category.INCOME:
            raise serializers.ValidationError("Choose an income account belonging to this school.")
        return value


class SchoolBillingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolBillingSettings
        fields = ["id", "receivables_account", "cash_account", "bank_account", "invoice_prefix", "receipt_prefix"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        school = self.context["school"]
        for field in ("receivables_account", "cash_account", "bank_account"):
            account = attrs.get(field, getattr(self.instance, field, None))
            if account and (account.school_id != school.id or account.category != Account.Category.ASSET):
                raise serializers.ValidationError({field: "Choose an asset account belonging to this school."})
        return attrs


class InvoiceLineInputSerializer(serializers.Serializer):
    fee_item = serializers.PrimaryKeyRelatedField(queryset=FeeItem.objects.all())
    description = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"), default=Decimal("1.00"))
    unit_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineInputSerializer(many=True, write_only=True, required=False)
    line_items = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "student", "student_name", "academic_year", "period", "invoice_number", "invoice_date", "due_date", "status", "notes", "lines", "line_items", "total_amount", "amount_paid", "balance", "journal_entry", "created_at"]
        read_only_fields = ["id", "invoice_number", "status", "journal_entry", "created_at", "total_amount", "amount_paid", "balance", "line_items"]

    def get_line_items(self, obj):
        return [{"id": line.id, "fee_item": line.fee_item_id, "fee_item_name": line.fee_item.name, "description": line.description, "quantity": line.quantity, "unit_amount": line.unit_amount, "amount": line.amount} for line in obj.lines.select_related("fee_item")]

    def validate(self, attrs):
        school = self.context["school"]
        student = attrs.get("student", getattr(self.instance, "student", None))
        year = attrs.get("academic_year", getattr(self.instance, "academic_year", None))
        period = attrs.get("period", getattr(self.instance, "period", None))
        if student and student.school_id != school.id:
            raise serializers.ValidationError({"student": "Student must belong to this school."})
        if year and year.school_id != school.id:
            raise serializers.ValidationError({"academic_year": "Academic year must belong to this school."})
        if period and period.school_id != school.id:
            raise serializers.ValidationError({"period": "Financial period must belong to this school."})
        for line in attrs.get("lines", []):
            if line["fee_item"].school_id != school.id:
                raise serializers.ValidationError({"lines": "All fee items must belong to this school."})
        return attrs

    def create(self, validated_data):
        from .services import _next_number
        from django.db import transaction
        lines = validated_data.pop("lines", [])
        school = self.context["school"]
        with transaction.atomic():
            number = _next_number(Invoice, school, "INV", "invoice_number")
            invoice = Invoice.objects.create(school=school, invoice_number=number, **validated_data)
            for line in lines:
                amount = (line["quantity"] * line["unit_amount"]).quantize(Decimal("0.01"))
                InvoiceLine.objects.create(invoice=invoice, amount=amount, **line)
        return invoice

    def update(self, instance, validated_data):
        if instance.status != Invoice.Status.DRAFT:
            raise serializers.ValidationError("Only draft invoices can be edited.")
        lines = validated_data.pop("lines", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                amount = (line["quantity"] * line["unit_amount"]).quantize(Decimal("0.01"))
                InvoiceLine.objects.create(invoice=instance, amount=amount, **line)
        return instance


class PaymentAllocationInputSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))


class PaymentSerializer(serializers.ModelSerializer):
    allocations = PaymentAllocationInputSerializer(many=True, write_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "student", "student_name", "receipt_number", "payment_date", "method", "amount", "transaction_reference", "notes", "allocations", "journal_entry", "created_at"]
        read_only_fields = ["id", "receipt_number", "journal_entry", "created_at"]

    def validate_student(self, value):
        if value.school_id != self.context["school"].id:
            raise serializers.ValidationError("Student must belong to this school.")
        return value

    def create(self, validated_data):
        from .services import record_payment
        allocations = validated_data.pop("allocations")
        return record_payment(
            school=self.context["school"], user=self.context["request"].user,
            allocations=allocations, **validated_data,
        )
