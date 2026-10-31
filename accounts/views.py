from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from auditlog.services import record_event

from .models import AcademicYear, ClassRoom, School, SchoolMembership, Student
from .permissions import SchoolRolePermission
from .serializers import (
    AcademicYearSerializer, ClassRoomSerializer, CreateSchoolSerializer,
    SchoolSerializer, StudentSerializer,
)


class SchoolViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return School.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_active=True,
        ).distinct()

    def get_serializer_class(self):
        return CreateSchoolSerializer if self.action == "create" else SchoolSerializer

    def perform_create(self, serializer):
        school = serializer.save()
        record_event(school=school, actor=self.request.user, action="SCHOOL_CREATED", entity_type="School", entity_id=school.pk, summary="Created school workspace")

    def perform_update(self, serializer):
        school = serializer.instance
        membership = SchoolMembership.objects.filter(
            school=school, user=self.request.user, is_active=True
        ).first()
        if not membership or membership.role not in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
            raise PermissionDenied("Only a school owner or administrator can update school settings.")
        instance = serializer.save()
        record_event(school=school, actor=self.request.user, action="SCHOOL_SETTINGS_UPDATED", entity_type="School", entity_id=school.pk, summary="Updated school settings")


class SchoolScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    school_lookup_kwarg = "school_pk"

    def get_school(self):
        if not hasattr(self, "_school"):
            self._school = get_object_or_404(
                School.objects.filter(
                    memberships__user=self.request.user,
                    memberships__is_active=True,
                    is_active=True,
                ).distinct(),
                pk=self.kwargs[self.school_lookup_kwarg],
            )
        return self._school

    def check_write_role(self):
        membership = SchoolMembership.objects.filter(
            school=self.get_school(), user=self.request.user, is_active=True
        ).first()
        if not membership or membership.role not in {
            SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN,
            SchoolMembership.Role.ACCOUNTANT, SchoolMembership.Role.BURSAR,
        }:
            raise PermissionDenied("Your school role does not permit this change.")

    def perform_create(self, serializer):
        self.check_write_role()
        instance = serializer.save(school=self.get_school())
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_CREATED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Created {instance.__class__.__name__}")

    def perform_update(self, serializer):
        self.check_write_role()
        instance = serializer.save()
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_UPDATED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Updated {instance.__class__.__name__}")

    def perform_destroy(self, instance):
        self.check_write_role()
        record_event(school=self.get_school(), actor=self.request.user, action=f"{instance.__class__.__name__.upper()}_DELETED", entity_type=instance.__class__.__name__, entity_id=instance.pk, summary=f"Deleted {instance.__class__.__name__}")
        instance.delete()


class StudentViewSet(SchoolScopedViewSet):
    serializer_class = StudentSerializer

    def get_queryset(self):
        return Student.objects.filter(school=self.get_school()).select_related("classroom")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "school": self.get_school()}


class AcademicYearViewSet(SchoolScopedViewSet):
    serializer_class = AcademicYearSerializer

    def get_queryset(self):
        return AcademicYear.objects.filter(school=self.get_school())


class ClassRoomViewSet(SchoolScopedViewSet):
    serializer_class = ClassRoomSerializer

    def get_queryset(self):
        return ClassRoom.objects.filter(school=self.get_school()).select_related("academic_year")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "school": self.get_school()}
