import base64
from unittest import TestCase
from unittest.mock import patch

import frappe

from ..client import get_active_notification_client
from frappe_notification import NotificationClientFixtures


class TestGetActiveNotificationClient(TestCase):
    clients = NotificationClientFixtures()

    @classmethod
    def setUpClass(cls) -> None:
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.clients.tearDown()

    def tearDown(self) -> None:
        frappe.local.notification_client = None

    @patch("frappe.get_request_header")
    def test_basic_auth_valid(self, mock_get_request_header):
        client = self.clients[0]
        api_key, api_secret = (client.api_key, client.get_password("api_secret"))

        basic_token = base64.b64encode(frappe.safe_encode(f"{api_key}:{api_secret}"))
        mock_get_request_header.return_value = f"Basic {basic_token}"

        r = get_active_notification_client()
        self.assertEqual(client.name, r)
