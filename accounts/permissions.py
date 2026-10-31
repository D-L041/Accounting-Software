from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import SchoolMembership


class SchoolRolePermission(BasePermission):
    """Role gate for school-scoped write operations."""

    write_roles = {
        SchoolMembership.Role.OWNER,
        SchoolMembership.Role.ADMIN,
        SchoolMembership.Role.ACCOUNTANT,
        SchoolMembership.Role.BURSAR,
    }

    def has_object_permission(self, request, view, obj):
        school = obj if hasattr(obj, "memberships") else getattr(obj, "school", None)
        if school is None:
            return False
        membership = SchoolMembership.objects.filter(
            school=school, user=request.user, is_active=True
        ).first()
        if membership is None:
            return False
        return request.method in SAFE_METHODS or membership.role in self.write_roles
