from unittest import TestCase
from unittest.mock import patch, MagicMock

import frappe

from frappe_notification import (
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationClientNotFound,
    set_active_notification_client,
)

from ..delete_template_doc import delete_template


class TestDeleteTemplate(TestCase):
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

    def test_simple_delete(self):
        """
        - A manager trying to delete a Template that he made
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        template = next(iter(self.templates.get_templates_created_by(manager))).name
        self.assertTrue(frappe.db.exists("Notification Template", template))

        r = delete_template(template)
        self.assertTrue(r)

        self.assertFalse(frappe.db.exists("Notification Template", template))

    def test_admin_delete(self):
        """
        - Admin will get ClientNotFound
        """
        with self.assertRaises(NotificationClientNotFound):
            delete_template(self.templates[0].name)

    @patch("frappe_notification.frappe_notification.controllers.templates.delete_template_doc."
           "validate_template_access")
    def test_make_sure_validate_access_was_called(self, mock_validate_template_access: MagicMock):
        """
        - Login as a manager client
        - Try deleting his own template
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        template = next(iter(self.templates.get_templates_created_by(manager))).name

        delete_template(template)

        mock_validate_template_access.assert_called_once_with(
            template=template, ptype="delete")
