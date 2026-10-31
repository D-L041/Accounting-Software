from django.db import transaction
from rest_framework import serializers

from .models import Account, BankStatement, BankStatementLine, FinancialPeriod, JournalEntry, JournalLine


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "code", "name", "category", "is_active"]
        read_only_fields = ["id"]


class FinancialPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialPeriod
        fields = ["id", "name", "starts_on", "ends_on", "is_locked"]
        read_only_fields = ["id", "is_locked"]

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError({"ends_on": "Financial period end must not precede its start."})
        return attrs


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalLine
        fields = ["id", "account", "account_code", "account_name", "description", "debit", "credit"]
        read_only_fields = ["id", "account_code", "account_name"]

    def validate(self, attrs):
        debit = attrs.get("debit", 0)
        credit = attrs.get("credit", 0)
        if debit < 0 or credit < 0:
            raise serializers.ValidationError("Journal amounts cannot be negative.")
        if (debit > 0) == (credit > 0):
            raise serializers.ValidationError("Each journal line must contain exactly one positive debit or credit.")
        return attrs


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_username", read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id", "reference", "description", "entry_date", "period", "period_name",
            "posted", "posted_at", "created_by_name", "created_at", "lines",
        ]
        read_only_fields = ["id", "posted", "posted_at", "created_by_name", "created_at"]

    def validate_period(self, value):
        if value.school_id != self.context["school"].id:
            raise serializers.ValidationError("Financial period must belong to this school.")
        return value

    def validate_lines(self, value):
        school = self.context["school"]
        if len(value) < 2:
            raise serializers.ValidationError("A journal requires at least two lines.")
        for line in value:
            if line["account"].school_id != school.id:
                raise serializers.ValidationError("Every account must belong to this school.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines")
        entry = JournalEntry.objects.create(
            school=self.context["school"],
            created_by=self.context["request"].user,
            **validated_data,
        )
        for line in lines:
            JournalLine.objects.create(entry=entry, **line)
        return entry

class BankStatementLineSerializer(serializers.ModelSerializer):
    matched_journal_reference = serializers.CharField(
        source="matched_journal_line.entry.reference", read_only=True
    )

    class Meta:
        model = BankStatementLine
        fields = [
            "id", "transaction_date", "description", "reference", "amount",
            "matched_journal_line", "matched_journal_reference", "created_at",
        ]
        read_only_fields = ["id", "matched_journal_line", "matched_journal_reference", "created_at"]


class BankStatementSerializer(serializers.ModelSerializer):
    lines = BankStatementLineSerializer(many=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    statement_movement = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    calculated_closing_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_statement_arithmetic_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = BankStatement
        fields = [
            "id", "account", "account_name", "period", "period_name",
            "statement_start", "statement_end", "opening_balance", "closing_balance",
            "status", "uploaded_by", "reconciled_at", "created_at", "lines",
            "statement_movement", "calculated_closing_balance", "is_statement_arithmetic_valid",
        ]
        read_only_fields = [
            "id", "status", "uploaded_by", "reconciled_at", "created_at",
            "account_name", "period_name", "statement_movement",
            "calculated_closing_balance", "is_statement_arithmetic_valid",
        ]

    def validate(self, attrs):
        school = self.context["school"]
        account = attrs.get("account", getattr(self.instance, "account", None))
        period = attrs.get("period", getattr(self.instance, "period", None))
        if account and (account.school_id != school.id or account.category != Account.Category.ASSET):
            raise serializers.ValidationError({"account": "Choose an asset account belonging to this school."})
        if period and period.school_id != school.id:
            raise serializers.ValidationError({"period": "Financial period must belong to this school."})
        if self.instance and self.instance.status != BankStatement.Status.DRAFT:
            raise serializers.ValidationError("A reconciled bank statement cannot be edited.")
        if not self.instance and not attrs.get("lines"):
            raise serializers.ValidationError({"lines": "Add at least one bank statement line."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines")
        statement = BankStatement.objects.create(
            school=self.context["school"],
            uploaded_by=self.context["request"].user,
            **validated_data,
        )
        for line in lines:
            BankStatementLine.objects.create(statement=statement, **line)
        return statement

