from unittest import TestCase, skip

import frappe

from frappe_notification import (
    NotificationTemplate,
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    set_active_notification_client,
)

from ..update_template_doc import update_template


class TestUpdateTemplate(TestCase):
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

    def tearDown(self) -> None:
        self.templates.tearDown()

    def test_simple_update(self):
        """
        - Login as a manager client
        - Try updating his own template
        """
        manager_1 = self.clients.get_manager_client().name
        set_active_notification_client(manager_1)

        template_1 = self.templates.get_templates_created_by(manager_1)[0]
        _updates = frappe._dict(
            subject=frappe.mock("first_name"),
            content=frappe.mock("last_name"),
            lang="ar",
        )

        r = update_template(
            template=template_1.name,
            updates=_updates
        )
        self.assertIsInstance(r, NotificationTemplate)

        template_1.reload()
        self.assertEqual(template_1.subject, _updates.subject)
        self.assertEqual(template_1.content, _updates.content)
        self.assertEqual(template_1.lang, _updates.lang)

    def test_update_allowed_clients(self):
        """
        - Login as a manager client
        - Try updating allowed clients on his template
        """
        manager_1 = self.clients.get_manager_client().name
        set_active_notification_client(manager_1)

        clients = [x.name for x in self.clients.get_clients_managed_by(manager_1)]
        allowed_clients = clients[0:2]

        template_1 = self.templates.get_templates_created_by(manager_1)[0]
        _updates = frappe._dict(
            allowed_clients=[
                dict(notification_client=x) for x in allowed_clients
            ]
        )

        r = update_template(
            template=template_1.name,
            updates=_updates
        )
        self.assertIsInstance(r, NotificationTemplate)

        template_1.reload()
        self.assertCountEqual(
            [x.notification_client for x in template_1.allowed_clients],
            allowed_clients
        )

    def test_updating_lang_templates(self):
        """
        - Login as a manager client
        - Try updating allowed clients on his template
        """
        manager_1 = self.clients.get_manager_client().name
        set_active_notification_client(manager_1)

        lang_templates = [
            frappe._dict(
                lang="ar",
                subject=frappe.mock("first_name"),
                content=frappe.mock("last_name"))]

        template_1 = self.templates.get_templates_created_by(manager_1)[0]
        _updates = frappe._dict(
            lang_templates=lang_templates
        )

        r = update_template(
            template=template_1.name,
            updates=_updates
        )
        self.assertIsInstance(r, NotificationTemplate)

        template_1.reload()
        self.assertCountEqual(
            [(x.lang, x.subject, x.content) for x in template_1.lang_templates],
            [(x.lang, x.subject, x.content) for x in lang_templates],
        )

    @skip("Channel Sender fixtures unavailable")
    def test_update_channel_senders(self):
        """
        - Updating channel_senders should be fine
        - TODO: We do not have Fixtures for any channel sender
        """
        pass

    def test_try_updating_prohibited_fields(self):
        """
        - Login as a manager client
        - Try updating his own template
        """
        manager_1 = self.clients.get_manager_client().name
        set_active_notification_client(manager_1)

        template_1 = self.templates.get_templates_created_by(manager_1)[0]
        _updates = frappe._dict(
            key=frappe.mock("first_name"),
            created_by=self.clients.get_non_manager_client().name,
            is_fork_of=self.templates[-1].name,
        )

        r = update_template(
            template=template_1.name,
            updates=_updates
        )
        self.assertIsInstance(r, NotificationTemplate)

        template_1.reload()
        self.assertNotEqual(template_1.key, _updates.key)
        self.assertNotEqual(template_1.created_by, _updates.created_by)
        self.assertNotEqual(template_1.is_fork_of, _updates.is_fork_of)
