from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AcademicYear, ClassRoom, School, SchoolMembership, Student


class SchoolModelTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="St Stephen School", code="st-stephen")

    def test_academic_year_must_end_after_start(self):
        year = AcademicYear(
            school=self.school, name="2026", starts_on=date(2026, 12, 31), ends_on=date(2026, 1, 1)
        )
        with self.assertRaises(ValidationError):
            year.full_clean()

    def test_class_must_use_own_school_academic_year(self):
        other = School.objects.create(name="Other School", code="other-school")
        year = AcademicYear.objects.create(
            school=other, name="2026", starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31)
        )
        classroom = ClassRoom(school=self.school, academic_year=year, name="Grade 1")
        with self.assertRaises(ValidationError):
            classroom.full_clean()

    def test_student_class_must_belong_to_same_school(self):
        other = School.objects.create(name="Other School", code="other-school")
        year = AcademicYear.objects.create(
            school=other, name="2026", starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31)
        )
        classroom = ClassRoom.objects.create(school=other, academic_year=year, name="Grade 1")
        student = Student(
            school=self.school, classroom=classroom, admission_number="A001",
            first_name="Test", last_name="Student", admission_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            student.full_clean()


class SchoolTenantAPITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(username="school-a", password="safe-test-password")
        self.user_b = user_model.objects.create_user(username="school-b", password="safe-test-password")
        self.school_a = School.objects.create(name="School A", code="school-a")
        self.school_b = School.objects.create(name="School B", code="school-b")
        SchoolMembership.objects.create(school=self.school_a, user=self.user_a, role="OWNER")
        SchoolMembership.objects.create(school=self.school_b, user=self.user_b, role="OWNER")
        self.student_a = Student.objects.create(
            school=self.school_a, admission_number="A001", first_name="Amina",
            last_name="Example", admission_date=date(2026, 1, 1),
        )
        self.student_b = Student.objects.create(
            school=self.school_b, admission_number="B001", first_name="Brian",
            last_name="Example", admission_date=date(2026, 1, 1),
        )
        self.client = APIClient()

    def test_user_can_only_list_students_in_their_school(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get(f"/api/schools/{self.school_a.pk}/students/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["admission_number"] for row in response.data], ["A001"])

    def test_user_cannot_access_another_school_students(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get(f"/api/schools/{self.school_b.pk}/students/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_create_school_and_become_owner(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post("/api/schools/", {"name": "New School", "code": "new-school"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SchoolMembership.objects.filter(
            school_id=response.data["id"], user=self.user_a, role="OWNER"
        ).exists())

    def test_read_only_member_cannot_create_student(self):
        SchoolMembership.objects.filter(school=self.school_a, user=self.user_a).update(role="VIEWER")
        self.client.force_authenticate(self.user_a)
        response = self.client.post(
            f"/api/schools/{self.school_a.pk}/students/",
            {"admission_number": "A002", "first_name": "New", "last_name": "Learner", "admission_date": "2026-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_read_only_member_cannot_delete_student(self):
        SchoolMembership.objects.filter(school=self.school_a, user=self.user_a).update(role="VIEWER")
        self.client.force_authenticate(self.user_a)
        response = self.client.delete(f"/api/schools/{self.school_a.pk}/students/{self.student_a.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Student.objects.filter(pk=self.student_a.pk).exists())

    def test_student_creation_is_audited(self):
        from auditlog.models import AuditEvent
        self.client.force_authenticate(self.user_a)
        response = self.client.post(
            f"/api/schools/{self.school_a.pk}/students/",
            {"admission_number": "A009", "first_name": "New", "last_name": "Learner", "admission_date": "2026-01-02"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(AuditEvent.objects.filter(
            school=self.school_a, action="STUDENT_CREATED", entity_id=str(response.data["id"])
        ).exists())


class SchoolMemberApiTests(TestCase):
    def setUp(self):
        from auditlog.models import AuditEvent
        self.User = get_user_model()
        self.owner = self.User.objects.create_user(username="member-owner", password="test-password")
        self.admin = self.User.objects.create_user(username="member-admin", password="test-password")
        self.school = School.objects.create(name="Membership School", code="membership-school")
        SchoolMembership.objects.create(school=self.school, user=self.owner, role=SchoolMembership.Role.OWNER)
        self.admin_membership = SchoolMembership.objects.create(school=self.school, user=self.admin, role=SchoolMembership.Role.ADMIN)
        self.client = APIClient()
        self.audit_model = AuditEvent

    def test_owner_can_create_school_user_with_hashed_password_and_audit_event(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/schools/{self.school.pk}/members/",
            {"username": "new-bursar", "password": "Complex-Test-Password-2026!", "role": "BURSAR", "email": "bursar@example.test"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        new_user = self.User.objects.get(username="new-bursar")
        self.assertTrue(new_user.check_password("Complex-Test-Password-2026!"))
        self.assertEqual(response.data["role"], "BURSAR")
        self.assertNotIn("password", response.data)
        self.assertTrue(self.audit_model.objects.filter(action="SCHOOL_MEMBER_CREATED", entity_id=str(response.data["id"])).exists())

    def test_administrator_cannot_assign_owner_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/schools/{self.school.pk}/members/",
            {"username": "bad-owner", "password": "Complex-Test-Password-2026!", "role": "OWNER"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.User.objects.filter(username="bad-owner").exists())

    def test_school_must_retain_at_least_one_active_owner(self):
        self.client.force_authenticate(self.owner)
        owner_membership = SchoolMembership.objects.get(school=self.school, user=self.owner)
        response = self.client.patch(
            f"/api/schools/{self.school.pk}/members/{owner_membership.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        owner_membership.refresh_from_db()
        self.assertTrue(owner_membership.is_active)

    def test_viewer_cannot_manage_school_members(self):
        viewer = self.User.objects.create_user(username="member-viewer", password="test-password")
        SchoolMembership.objects.create(school=self.school, user=viewer, role=SchoolMembership.Role.VIEWER)
        self.client.force_authenticate(viewer)
        response = self.client.get(f"/api/schools/{self.school.pk}/members/")
        self.assertEqual(response.status_code, 403)


class OfflinePurchaseOrderSyncTests(TestCase):
    def setUp(self):
        from datetime import date
        from expenses.models import Supplier
        from ledger.models import FinancialPeriod
        self.user = get_user_model().objects.create_user(username="offline-po-owner", password="test-password")
        self.school = School.objects.create(name="Offline PO School", code="offline-po-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role=SchoolMembership.Role.OWNER)
        self.period = FinancialPeriod.objects.create(
            school=self.school, name="FY2026", starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31)
        )
        self.supplier = Supplier.objects.create(school=self.school, name="Approved Test Supplier")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/schools/{self.school.pk}/offline-sync/"
        self.key = "a8f3b84a-21b7-4e92-8ef0-4f47bff4a5a0"
        self.payload = {
            "supplier": self.supplier.pk,
            "period": self.period.pk,
            "order_date": "2026-10-01",
            "expected_date": "2026-10-15",
            "description": "Offline stationery order",
            "lines": [
                {"description": "Exercise books", "quantity": "10.000", "unit_cost": "75.00"},
                {"description": "Pens", "quantity": "20.000", "unit_cost": "15.00"},
            ],
        }

    def sync(self, payload=None, key=None):
        return self.client.post(self.url, {
            "resource_type": "purchase_order",
            "idempotency_key": key or self.key,
            "payload": payload or self.payload,
        }, format="json")

    def test_purchase_order_sync_creates_non_submitted_draft_and_is_idempotent(self):
        from expenses.models import PurchaseOrder
        first = self.sync()
        self.assertEqual(first.status_code, 201, first.data)
        order = PurchaseOrder.objects.get(pk=first.data["purchase_order_id"])
        self.assertEqual(order.status, PurchaseOrder.Status.DRAFT)
        self.assertEqual(order.lines.count(), 2)
        self.assertEqual(str(order.total_amount), "1050.00")
        retry = self.sync()
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(retry.data["status"], "already_applied")
        self.assertEqual(PurchaseOrder.objects.filter(school=self.school).count(), 1)

    def test_reusing_sync_key_with_different_payload_returns_conflict(self):
        first = self.sync()
        self.assertEqual(first.status_code, 201, first.data)
        changed = {**self.payload, "description": "Changed after first delivery"}
        response = self.sync(payload=changed)
        self.assertEqual(response.status_code, 409)
        from expenses.models import PurchaseOrder
        self.assertEqual(PurchaseOrder.objects.filter(school=self.school).count(), 1)

    def test_purchase_order_sync_rejects_supplier_from_another_school(self):
        from expenses.models import Supplier
        other = School.objects.create(name="Other Offline PO School", code="other-offline-po-school")
        foreign_supplier = Supplier.objects.create(school=other, name="Foreign Supplier")
        payload = {**self.payload, "supplier": foreign_supplier.pk}
        response = self.sync(payload=payload)
        self.assertEqual(response.status_code, 400)
        from expenses.models import PurchaseOrder
        self.assertFalse(PurchaseOrder.objects.filter(school=self.school).exists())

    def test_viewer_cannot_sync_purchase_order(self):
        SchoolMembership.objects.filter(school=self.school, user=self.user).update(role=SchoolMembership.Role.VIEWER)
        response = self.sync()
        self.assertEqual(response.status_code, 403)
