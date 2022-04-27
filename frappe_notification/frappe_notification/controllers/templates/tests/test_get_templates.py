from unittest import TestCase

import frappe
from frappe_notification import (
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationClientNotFound,
    # NotificationTemplateNotFound,
    set_active_notification_client)
from ..get_templates import get_templates


class TestGetTemplate(TestCase):
    clients = NotificationClientFixtures()
    templates = NotificationTemplateFixtures()

    @classmethod
    def setUpClass(cls):
        cls.clients.setUp()
        cls.templates.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.templates.tearDown()
        cls.clients.tearDown()

    def setUp(self) -> None:
        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        set_active_notification_client(None)

    def test_simple(self):
        """
        - Login as a Manager Client
        - Ask for all templates he can access
        """
        client = self.clients.get_manager_client().name
        set_active_notification_client(client)

        templates = get_templates()
        self.assertGreater(len(templates), 0)

        for t in templates:
            self.assertIsNotNone(t.name)
            self.assertIsNotNone(t.key)
            self.assertIsNotNone(t.subject)
            self.assertEqual(t.created_by, client)

    def test_admin(self):
        """
        - Login as Administrator (not a Client)
        - He will not have access to any templates
        """
        frappe.set_user("Administrator")

        _template = self.templates[0]
        self.assertIsNotNone(_template)

        with self.assertRaises(NotificationClientNotFound):
            get_templates()

    def test_subordinate(self):
        """
        - Login as a subordinate
        - Ask for all templates he can access
        - He should get templates that his manager allowed him access
        """

        manager_1 = self.clients.get_manager_client().name
        client_m1 = self.clients.get_clients_managed_by(manager_1)[0].name

        set_active_notification_client(client_m1)

        templates = get_templates()
        self.assertGreater(len(templates), 0)

        for t in templates:
            self.assertIsNotNone(t.name)
            self.assertIsNotNone(t.key)
            self.assertIsNotNone(t.subject)

            self.assertTrue(any([
                t.created_by == client_m1,
                t.created_by == manager_1
            ]))
