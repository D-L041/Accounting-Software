import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, Client

from .models import C2BNotification
from .services import normalize_phone


class DarajaPhoneTests(SimpleTestCase):
    def test_normalizes_local_mobile_number(self):
        self.assertEqual(normalize_phone("0712345678"), "254712345678")

    def test_accepts_international_mobile_number(self):
        self.assertEqual(normalize_phone("+254 712 345 678"), "254712345678")

    def test_rejects_invalid_number(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            normalize_phone("12345")


class C2BCallbackTests(TestCase):
    def test_duplicate_confirmation_is_captured_once(self):
        client = Client()
        payload = {
            "TransID": "QWERTY12345", "TransAmount": "1000.00",
            "BillRefNumber": "INV-000001", "BusinessShortCode": "123456",
            "MSISDN": "254712345678", "TransTime": "20261031120000",
        }
        with patch.dict("os.environ", {"DARAJA_SHORTCODE": "123456"}):
            first = client.post(
                "/api/daraja/callbacks/c2b/confirmation/",
                data=json.dumps(payload), content_type="application/json",
            )
            second = client.post(
                "/api/daraja/callbacks/c2b/confirmation/",
                data=json.dumps(payload), content_type="application/json",
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(C2BNotification.objects.filter(transaction_id="QWERTY12345").count(), 1)
        self.assertEqual(C2BNotification.objects.get(transaction_id="QWERTY12345").status,
                         C2BNotification.Status.RECEIVED)
