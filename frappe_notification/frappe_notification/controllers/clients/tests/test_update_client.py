from unittest import TestCase
from unittest.mock import patch, MagicMock

import frappe
from frappe_notification import (
    NotificationClient,
    NotificationClientFixtures,
    set_active_notification_client
)

from ..update_client import update_notification_client


class TestUpdateClient(TestCase):
    clients = NotificationClientFixtures()

    def setUp(self):
        self.clients.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self):
        set_active_notification_client(None)
        frappe.set_user("Administrator")

        self.clients.tearDown()

    def test_simple_update(self):
        """
        A manager updating one of its subordinate
        """
        manager_1 = self.clients.get_manager_client().name
        set_active_notification_client(manager_1)

        client_1 = self.clients.get_clients_managed_by(manager_1)[0].name
        _updates = frappe._dict(
            title=frappe.mock("first_name"),
            url=frappe.mock("url")
        )

        r = update_notification_client(client=client_1, data=_updates)
        self.assertIsInstance(r, NotificationClient)

        self.assertEqual(r.title, _updates.title)
        self.assertEqual(r.url, _updates.url)

    @patch("frappe_notification.frappe_notification.controllers.clients.update_client."
           "validate_client_access")
    def test_make_sure_validate_access_was_called(self, mock_validate_client_access: MagicMock):
        """
        - Login as a Manager
        - Make sure validate_access was called. All perm checks happen inside it
        - This should be enough perm test check
        """

        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        client = self.clients.get_clients_managed_by(manager)[0].name
        self.assertIsNotNone(client)

        t = update_notification_client(client, dict(title="B"))
        self.assertIsInstance(t, NotificationClient)

        mock_validate_client_access.assert_called_once_with(client=client)

    def test_try_setting_forbidden_fields(self):
        """
        Fields like api_key, api_secret, managed_by etc cannot be controlled
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        manager_2 = None
        while manager_2 is None or manager_2 == manager:
            manager_2 = self.clients.get_manager_client().name

        client = self.clients.get_clients_managed_by(manager)[0].name

        _data = frappe._dict(
            title=frappe.mock("first_name"),
            url=frappe.mock("url"),

            api_key="A",
            api_secret="B",
            managed_by=manager_2
        )
        r = update_notification_client(client=client, data=_data)

        self.assertNotEqual(_data.api_key, r.api_key)
        self.assertNotEqual(_data.api_secret, r.api_secret)
        self.assertNotEqual(_data.managed_by, r.managed_by)
