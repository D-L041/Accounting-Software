from django.db import transaction
from rest_framework import serializers

from .models import Account, FinancialPeriod, JournalEntry, JournalLine


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
