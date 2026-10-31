from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import School
from ledger.models import FinancialPeriod
from ledger.services import (
    build_balance_sheet,
    build_cashbook,
    build_income_expenditure_statement,
    build_trial_balance,
)


class SchoolReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_period(self, request, school_pk):
        school = get_object_or_404(
            School.objects.filter(
                memberships__user=request.user,
                memberships__is_active=True,
                is_active=True,
            ).distinct(),
            pk=school_pk,
        )
        period_id = request.query_params.get("period")
        if not period_id:
            raise ValidationError({"period": "Select a financial period."})
        return get_object_or_404(FinancialPeriod, school=school, pk=period_id)


class TrialBalanceView(SchoolReportView):
    def get(self, request, school_pk):
        return Response(build_trial_balance(self.get_period(request, school_pk)))


class IncomeExpenditureView(SchoolReportView):
    def get(self, request, school_pk):
        return Response(build_income_expenditure_statement(self.get_period(request, school_pk)))


class BalanceSheetView(SchoolReportView):
    def get(self, request, school_pk):
        return Response(build_balance_sheet(self.get_period(request, school_pk)))


class CashbookView(SchoolReportView):
    def get(self, request, school_pk):
        return Response(build_cashbook(self.get_period(request, school_pk)))


class CashFlowView(SchoolReportView):
    def get(self, request, school_pk):
        period = self.get_period(request, school_pk)
        report = build_cashbook(period)
        return Response({
            "period": report["period"],
            "basis": "Direct cash and bank movement from posted ledger entries",
            "opening_balance_included": False,
            "total_inflows": report["total_receipts"],
            "total_outflows": report["total_payments"],
            "net_cash_movement": report["net_movement"],
            "transactions": report["transactions"],
        })
