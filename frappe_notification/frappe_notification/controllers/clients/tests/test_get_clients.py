from unittest import TestCase

import frappe
from frappe_notification import (
    NotificationClientFixtures,
    PermissionDenied,
    set_active_notification_client
)

from ..get_clients import get_notification_clients


class TestGetClients(TestCase):
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

    def test_simple_get_clients(self):
        """
        A manager asking for all clients he manage
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        clients = get_notification_clients()

        self.assertEqual(len(clients), len(self.clients.get_clients_managed_by(manager)))

        for client in clients:
            self.assertIsNotNone(client.name)
            self.assertIsNotNone(client.title)
            self.assertIsNotNone(client.url)
            self.assertEqual(
                manager,
                frappe.db.get_value("Notification Client", client.name, "managed_by")
            )

    def test_non_managers(self):
        with self.assertRaises(PermissionDenied):
            get_notification_clients()

        client = self.clients.get_non_manager_client().name
        set_active_notification_client(client)

        with self.assertRaises(PermissionDenied):
            get_notification_clients()
