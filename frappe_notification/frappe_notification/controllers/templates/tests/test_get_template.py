from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe
from frappe_notification import (
    NotificationTemplate,
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationClientNotFound,
    # NotificationTemplateNotFound,
    set_active_notification_client)
from ..get_template_doc import get_template


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
        - Login as a Client
        - Ask for a template he owns
        """
        client = self.clients.get_manager_client().name
        set_active_notification_client(client)

        _template = next(iter(self.templates.get_templates_created_by(client)), None)
        self.assertIsNotNone(_template)

        t = get_template(_template.name)
        self.assertIsInstance(t, NotificationTemplate)
        self.assertEqual(t.name, _template.name)

    def test_admin(self):
        """
        - Login as Administrator (not a Client)
        - He will not have access to any templates
        """
        frappe.set_user("Administrator")

        _template = self.templates[0]
        self.assertIsNotNone(_template)

        with self.assertRaises(NotificationClientNotFound):
            get_template(_template.name)

    @patch("frappe_notification.frappe_notification.controllers.templates.get_template_doc."
           "validate_template_access")
    def test_make_sure_validate_access_was_called(self, mock_validate_template_access: MagicMock):
        """
        - Login as a Client
        - Make sure validate_access was called. All perm checks happen inside it
        """

        client = self.clients.get_manager_client().name
        set_active_notification_client(client)

        _template = next(iter(self.templates.get_templates_created_by(client)), None)
        self.assertIsNotNone(_template)

        t = get_template(_template.name)
        self.assertIsInstance(t, NotificationTemplate)
        mock_validate_template_access.assert_called_once_with(template=_template.name)
