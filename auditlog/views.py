from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from accounts.models import School, SchoolMembership
from .models import AuditEvent
from .serializers import AuditEventSerializer


class SchoolAuditEventListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        school = get_object_or_404(
            School.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                is_active=True,
            ).distinct(),
            pk=self.kwargs["school_pk"],
        )
        membership = SchoolMembership.objects.filter(
            school=school, user=self.request.user, is_active=True
        ).first()
        if not membership or membership.role not in {
            SchoolMembership.Role.OWNER,
            SchoolMembership.Role.ADMIN,
            SchoolMembership.Role.ACCOUNTANT,
        }:
            raise PermissionDenied("Your school role does not permit viewing the audit log.")
        return AuditEvent.objects.filter(school=school).select_related("actor")
