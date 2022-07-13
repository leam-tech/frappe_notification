from unittest import TestCase
from unittest.mock import patch, MagicMock

import frappe
from frappe_notification import (
    NotificationClient,
    NotificationClientFixtures,
    set_active_notification_client
)

from ..get_client import get_notification_client


class TestGetClient(TestCase):
    clients: NotificationClientFixtures = None

    @classmethod
    def setUpClass(cls):
        cls.clients = NotificationClientFixtures()
        cls.clients.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    @classmethod
    def tearDownClass(cls):
        set_active_notification_client(None)
        frappe.set_user("Administrator")

        cls.clients.tearDown()

    def test_simple(self):
        """
        Manager asking for one of his subordinate
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        client = self.clients.get_clients_managed_by(manager)[0].name
        t = get_notification_client(client=client)

        self.assertIsInstance(t, NotificationClient)
        self.assertEqual(t.name, client)

    @patch("frappe_notification.frappe_notification.controllers.clients.get_client."
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

        t = get_notification_client(client)
        self.assertIsInstance(t, NotificationClient)

        mock_validate_client_access.assert_called_once_with(client=client)
