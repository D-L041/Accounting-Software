from django.test import TestCase
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    def test_health_check_confirms_database_connectivity(self):
        response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok", "database": "ok"})
