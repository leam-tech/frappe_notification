from unittest import TestCase

import frappe
from frappe_notification import (
    NotificationClient,
    NotificationClientFixtures,
    PermissionDenied,
    set_active_notification_client
)

from ..create_client import create_notification_client


class TestCreateClient(TestCase):
    clients: NotificationClientFixtures = None

    def setUp(self):
        self.clients = NotificationClientFixtures()
        self.clients.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self):
        set_active_notification_client(None)
        frappe.set_user("Administrator")

        self.clients.tearDown()

    def test_simple_creation(self):
        """
        - As a manager, he can create new Clients
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        r = create_notification_client(frappe._dict(
            title=frappe.mock("first_name"),
            url=frappe.mock("url"),
        ))
        self.clients.add_document(r)

        self.assertIsInstance(r, NotificationClient)
        self.assertTrue(frappe.db.exists("Notification Client", r.name))

        self.assertIsNotNone(r.api_key)
        self.assertIsNotNone(r.api_secret)
        self.assertNotEqual(r.api_secret, "*" * len(r.api_secret))

    def test_non_managers(self):
        """
        - Non-managers and when no active clients are available, it should raise
        """
        with self.assertRaises(PermissionDenied):
            create_notification_client(dict(title="A"))

        client = self.clients.get_non_manager_client().name
        set_active_notification_client(client)

        with self.assertRaises(PermissionDenied):
            create_notification_client(dict(title="A"))

    def test_try_setting_forbidden_fields(self):
        """
        Fields like api_key, api_secret, managed_by etc cannot be controlled
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        manager_2 = None
        while manager_2 is None or manager_2 == manager:
            manager_2 = self.clients.get_manager_client().name

        _data = frappe._dict(
            title=frappe.mock("first_name"),
            url=frappe.mock("url"),

            api_key="A",
            api_secret="B",
            managed_by=manager_2
        )
        r = create_notification_client(data=_data)
        self.clients.add_document(r)

        self.assertNotEqual(_data.api_key, r.api_key)
        self.assertNotEqual(_data.api_secret, r.api_secret)
        self.assertNotEqual(_data.managed_by, r.managed_by)
