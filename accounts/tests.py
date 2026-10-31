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
