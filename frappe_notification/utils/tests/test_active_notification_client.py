import base64
from unittest import TestCase
from unittest.mock import patch, MagicMock

import frappe

from ..client import get_active_notification_client, set_active_notification_client
from frappe_notification import NotificationClient, NotificationClientFixtures


def patch_get_request_header(fn):
    def _inner(*args, **kwargs):
        with patch.object(frappe, "request", dict(headers=dict(a=1))):
            with patch("frappe.get_request_header") as p:
                return fn(*args, p, **kwargs)

    return _inner


class TestGetActiveNotificationClient(TestCase):
    clients: NotificationClientFixtures = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.clients = NotificationClientFixtures()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.clients.tearDown()

    def tearDown(self) -> None:
        set_active_notification_client(None)

    def base64_encode(self, txt: str):
        return frappe.safe_decode(base64.b64encode(
            frappe.safe_encode(txt)))

    def get_basic_token(self, client: NotificationClient):
        api_key, api_secret = (client.api_key, client.get_password("api_secret"))
        return self.base64_encode(f"{api_key}:{api_secret}")

    def get_token(self, client: NotificationClient):
        api_key, api_secret = (client.api_key, client.get_password("api_secret"))
        return f"{api_key}:{api_secret}"

    @patch_get_request_header
    def test_basic_auth_valid(self, mock_get_request_header: MagicMock):
        client = self.clients[0]

        mock_get_request_header.return_value = f"Basic {self.get_basic_token(client)}"

        r = get_active_notification_client()
        self.assertEqual(client.name, r)

    @patch_get_request_header
    def test_basic_auth_invalid(self, mock_get_request_header: MagicMock):
        client = self.clients[0]

        mock_get_request_header.return_value = f"Basic a{self.get_basic_token(client)}"

        r = get_active_notification_client()
        self.assertEqual(r, None)

    @patch_get_request_header
    def test_token_auth_valid(self, mock_get_request_header: MagicMock):
        client = self.clients[0]

        mock_get_request_header.return_value = f"Token {self.get_token(client)}"

        r = get_active_notification_client()
        self.assertEqual(client.name, r)

    @patch_get_request_header
    def test_token_auth_invalid(self, mock_get_request_header: MagicMock):
        client = self.clients[0]

        mock_get_request_header.return_value = f"Token a{self.get_token(client)}"

        r = get_active_notification_client()
        self.assertEqual(r, None)

    @patch_get_request_header
    def test_set_active_client(self, mock_get_request_header: MagicMock):
        client = self.clients[0]
        mock_get_request_header.return_value = None

        self.assertEqual(get_active_notification_client(), None)

        set_active_notification_client(client.name)

        self.assertEqual(get_active_notification_client(), client.name)
