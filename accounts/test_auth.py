from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import School, SchoolMembership


class SessionAuthenticationApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="school-owner", password="Strong-password-2026")
        self.school = School.objects.create(name="St Stephen School", code="auth-school")
        SchoolMembership.objects.create(school=self.school, user=self.user, role=SchoolMembership.Role.OWNER)
        self.client = APIClient(enforce_csrf_checks=True)

    def test_login_requires_csrf_and_returns_school_memberships(self):
        csrf = self.client.get("/api/auth/csrf/")
        self.assertEqual(csrf.status_code, 200)
        response = self.client.post(
            "/api/auth/login/",
            {"username": "school-owner", "password": "Strong-password-2026"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf.data["csrfToken"],
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["user"]["schools"][0]["id"], self.school.pk)
        current = self.client.get("/api/auth/me/")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data["user"]["username"], "school-owner")

    def test_invalid_credentials_are_rejected(self):
        csrf = self.client.get("/api/auth/csrf/")
        response = self.client.post(
            "/api/auth/login/",
            {"username": "school-owner", "password": "wrong"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf.data["csrfToken"],
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_ends_session(self):
        csrf = self.client.get("/api/auth/csrf/")
        self.client.post(
            "/api/auth/login/",
            {"username": "school-owner", "password": "Strong-password-2026"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf.data["csrfToken"],
        )
        current = self.client.get("/api/auth/csrf/")
        response = self.client.post(
            "/api/auth/logout/", {}, format="json",
            HTTP_X_CSRFTOKEN=current.data["csrfToken"],
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)
