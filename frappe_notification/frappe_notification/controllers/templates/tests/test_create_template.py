from unittest import TestCase

import frappe

from frappe_notification import (
    NotificationTemplate,
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationClientNotFound,
    set_active_notification_client,
)

from ..create_template_doc import create_template


class TestCreateTemplate(TestCase):
    clients = NotificationClientFixtures()
    templates = NotificationTemplateFixtures()

    @classmethod
    def setUpClass(cls):
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()

    def setUp(self):
        self.templates.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        set_active_notification_client(None)

        self.templates.tearDown()

    def test_simple(self):
        """
        - Login as manager client
        - Try creating a full blown Template
        """
        manager_1 = self.clients.get_manager_client().name
        set_active_notification_client(manager_1)

        data = frappe._dict(
            key="MY_NEW_TEMPLATE_187",
            subject=frappe.mock("first_name"),
            content=frappe.mock("last_name"),
            lang="ar",
            allowed_clients=[
                dict(notification_client=x.name)
                for x in self.clients.get_clients_managed_by(manager_1)
            ],
            lang_templates=[
                dict(lang="en-US",
                     content=frappe.mock("first_name"),
                     subject=frappe.mock("first_name"))
            ]
        )

        r = create_template(
            data=data
        )
        self.templates.add_document(r)
        self.assertIsInstance(r, NotificationTemplate)

        self.assertEqual(r.created_by, manager_1)
        self.assertEqual(r.subject, data.subject)
        self.assertEqual(len(r.lang_templates), len(data.lang_templates))
        self.assertEqual(len(r.allowed_clients), len(data.allowed_clients))

    def test_non_client(self):
        with self.assertRaises(NotificationClientNotFound):
            create_template(dict(subject="A"))

        frappe.set_user("Administrator")
        with self.assertRaises(NotificationClientNotFound):
            create_template(dict(subject="A"))
