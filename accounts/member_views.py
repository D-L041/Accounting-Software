from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from auditlog.services import record_event
from .models import School, SchoolMembership
from .member_serializers import SchoolMemberCreateSerializer, SchoolMemberSerializer


class SchoolMemberAccessMixin:
    permission_classes = [permissions.IsAuthenticated]

    def get_school(self):
        return get_object_or_404(
            School.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                is_active=True,
            ).distinct(),
            pk=self.kwargs["school_pk"],
        )

    def get_requester_membership(self):
        membership = SchoolMembership.objects.filter(
            school=self.get_school(), user=self.request.user, is_active=True
        ).first()
        if not membership or membership.role not in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
            raise PermissionDenied("Only school owners and administrators can manage school users.")
        return membership


class SchoolMemberListCreateView(SchoolMemberAccessMixin, generics.ListCreateAPIView):
    def get_queryset(self):
        self.get_requester_membership()
        return SchoolMembership.objects.filter(school=self.get_school()).select_related("user").order_by("user__username")

    def get_serializer_class(self):
        return SchoolMemberCreateSerializer if self.request.method == "POST" else SchoolMemberSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        requester = self.get_requester_membership()
        role = serializer.validated_data["role"]
        if requester.role == SchoolMembership.Role.ADMIN and role in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
            raise PermissionDenied("Administrators cannot create owners or other administrators.")
        data = serializer.validated_data
        User = get_user_model()
        user = User.objects.create_user(
            username=data["username"],
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            password=data["password"],
        )
        membership = SchoolMembership.objects.create(school=self.get_school(), user=user, role=role)
        record_event(
            school=self.get_school(), actor=self.request.user, action="SCHOOL_MEMBER_CREATED",
            entity_type="SchoolMembership", entity_id=membership.pk,
            summary=f"Added school user {user.username}",
            metadata={"role": role, "membership_id": membership.pk},
        )


class SchoolMemberDetailView(SchoolMemberAccessMixin, generics.RetrieveUpdateAPIView):
    serializer_class = SchoolMemberSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        self.get_requester_membership()
        return SchoolMembership.objects.filter(school=self.get_school()).select_related("user")

    @transaction.atomic
    def perform_update(self, serializer):
        requester = self.get_requester_membership()
        target = serializer.instance
        requested_role = serializer.validated_data.get("role", target.role)
        requested_active = serializer.validated_data.get("is_active", target.is_active)
        if requester.role == SchoolMembership.Role.ADMIN:
            if target.role in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
                raise PermissionDenied("Administrators cannot modify owners or other administrators.")
            if requested_role in {SchoolMembership.Role.OWNER, SchoolMembership.Role.ADMIN}:
                raise PermissionDenied("Administrators cannot assign owner or administrator roles.")
        if target.role == SchoolMembership.Role.OWNER and (
            requested_role != SchoolMembership.Role.OWNER or not requested_active
        ):
            active_owners = SchoolMembership.objects.select_for_update().filter(
                school=target.school, role=SchoolMembership.Role.OWNER, is_active=True
            ).count()
            if active_owners <= 1:
                raise ValidationError("A school must retain at least one active owner.")
        updated = serializer.save()
        record_event(
            school=target.school, actor=self.request.user, action="SCHOOL_MEMBER_UPDATED",
            entity_type="SchoolMembership", entity_id=updated.pk,
            summary=f"Updated access for school user {updated.user.username}",
            metadata={"role": updated.role, "is_active": updated.is_active},
        )
