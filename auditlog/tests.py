from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership
from .models import AuditEvent


class AuditLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="auditor", password="test-password")
        self.school = School.objects.create(name="Audit School", code="audit-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role=SchoolMembership.Role.ACCOUNTANT)
        self.event = AuditEvent.objects.create(
            school=self.school, actor=self.user, action="TEST_EVENT",
            entity_type="TestRecord", entity_id="42", summary="Audit test event",
            metadata={"amount": "100.00"},
        )

    def test_audit_events_are_immutable(self):
        with self.assertRaises(ValidationError):
            self.event.save()
        with self.assertRaises(ValidationError):
            self.event.delete()
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=self.event.pk).update(summary="tampered")
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=self.event.pk).delete()

    def test_school_member_can_read_own_audit_events(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f"/api/schools/{self.school.pk}/audit/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["entity_id"], "42")

    def test_other_school_events_are_not_visible(self):
        other = School.objects.create(name="Other Audit School", code="other-audit-school")
        AuditEvent.objects.create(
            school=other, actor=self.user, action="PRIVATE",
            entity_type="TestRecord", entity_id="99", summary="Other school",
        )
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f"/api/schools/{self.school.pk}/audit/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_viewer_cannot_read_audit_log(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role=SchoolMembership.Role.VIEWER)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get(f"/api/schools/{self.school.pk}/audit/")
        self.assertEqual(response.status_code, 403)
