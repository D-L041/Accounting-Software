from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import School
from ledger.models import FinancialPeriod
from ledger.services import build_trial_balance


class TrialBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, school_pk):
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
        period = get_object_or_404(FinancialPeriod, school=school, pk=period_id)
        return Response(build_trial_balance(period))
