from unittest import TestCase

import frappe

from frappe_notification import (
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationClientNotFound,
    set_active_notification_client,
)

from ..fork_template_doc import fork_template


class TestForkTemplate(TestCase):
    clients: NotificationClientFixtures = None
    templates: NotificationTemplateFixtures = None

    @classmethod
    def setUpClass(cls):
        cls.clients = NotificationClientFixtures()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()

    def setUp(self):
        self.templates = NotificationTemplateFixtures()
        self.templates.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        set_active_notification_client(None)

        self.templates.tearDown()

    def test_simple(self):
        manager_1 = self.clients.get_manager_client().name
        client_1 = next(iter(self.clients.get_clients_managed_by(manager_1)))
        set_active_notification_client(client_1.name)

        template = self.templates.get_templates_created_by(manager_1)[0]
        forked_template = fork_template(template=template.name)
        self.templates.add_document(forked_template)

        self.assertEqual(forked_template.is_fork_of, template.name)
        self.assertEqual(forked_template.created_by, client_1.name)

    def test_non_client(self):
        with self.assertRaises(NotificationClientNotFound):
            fork_template(self.templates[0].name)

        frappe.set_user("Administrator")
        with self.assertRaises(NotificationClientNotFound):
            fork_template(self.templates[0].name)
