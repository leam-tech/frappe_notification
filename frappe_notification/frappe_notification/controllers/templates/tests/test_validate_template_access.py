from unittest import TestCase
from typing import Any, Iterable, Optional

import frappe

from frappe_notification import (
    NotificationTemplate,
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationClientNotFound,
    NotificationTemplateNotFound,
    set_active_notification_client)

from ..utils import validate_template_access


class TestValidateTemplateAccess(TestCase):
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

    def setUp(self):
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        set_active_notification_client(None)

    def test_active_client_comes_first_and_foremost(self):
        """
        Before any validations start, there should be an active notification-client
        Make sure no other exception will be raised as long as active-client = Nones
        """
        # with valid template name
        with self.assertRaises(NotificationClientNotFound):
            validate_template_access(self.templates[0].name)

        # with invalid template name
        with self.assertRaises(NotificationClientNotFound):
            validate_template_access("non-existent-template")

        client = self.clients.get_manager_client().name
        set_active_notification_client(client)
        template = self._get_first(
            self.templates.get_templates_created_by(client),
            frappe._dict(name=None)).name
        self.assertIsNotNone(template)

        validate_template_access(template)

    def test_non_existent_template(self):
        """
        When template is non-existent, TemplateNotFound should be raised
        """
        client = self.clients.get_manager_client().name
        set_active_notification_client(client)

        with self.assertRaises(NotificationTemplateNotFound):
            validate_template_access("non-existent-template")

    def test_manager_asking_for_his_own_template(self):
        """
        A Manager asking for template that he himself created
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        template = self._get_first(
            self.templates.get_templates_created_by(manager),
            frappe._dict(name=None)).name
        self.assertIsNotNone(template)

        validate_template_access(template)

    def test_manager_asking_for_a_template_created_by_subordinate(self):
        """
        A Manager asking for templates that was created by his subordinate clients
        Permission will be denied
        """
        manager = self.clients.get_manager_client().name
        client = self._get_first_obj(self.clients.get_clients_managed_by(manager)).name

        template = self._get_template_created_by(client)

        set_active_notification_client(manager)

        with self.assertRaises(NotificationTemplateNotFound):
            validate_template_access(template.name)

    def test_manager_asking_for_another_managers_template(self):
        """
        A Manager asking for a template created by another Manager
        Permission will be denied
        """
        manager_1 = self.clients.get_manager_client().name
        manager_2 = self.clients.get_manager_client().name
        while manager_1 == manager_2:
            manager_2 = self.clients.get_manager_client().name

        template_m2 = self._get_template_created_by(manager_2).name

        set_active_notification_client(manager_1)

        with self.assertRaises(NotificationTemplateNotFound):
            validate_template_access(template_m2)

    def test_manager_asking_for_another_manager_subordinate_template(self):
        """
        A Manager asking for a template created by another Manager's subordinate
        Permission will be denied
        """
        manager_1 = self.clients.get_manager_client().name
        manager_2 = self.clients.get_manager_client().name
        while manager_1 == manager_2:
            manager_2 = self.clients.get_manager_client().name

        client_m2 = self._get_first_obj(self.clients.get_clients_managed_by(manager_2)).name
        template_cm2 = self._get_template_created_by(client_m2).name

        set_active_notification_client(manager_1)

        with self.assertRaises(NotificationTemplateNotFound):
            validate_template_access(template_cm2)

    def test_subordinate_asking_for_template_made_by_manager_allowed(self):
        """
        A Subordinate asking for a Template made by his manager, which is allowed for him to access
        """
        manager_1 = self.clients.get_manager_client().name
        client_m1 = self._get_first_obj(self.clients.get_clients_managed_by(manager_1)).name

        template_m1 = self._get_template_created_by(manager_1)
        template_m1.append("allowed_clients", dict(notification_client=client_m1))
        template_m1.save(ignore_permissions=True)
        self.assertEqual(template_m1.created_by, manager_1)

        set_active_notification_client(client_m1)
        validate_template_access(template_m1.name)

    def test_subordinate_asking_for_template_made_by_manager_denied(self):
        """
        A Subordinate asking for a Template made by his manager which is denied to him
        """
        manager_1 = self.clients.get_manager_client().name
        client_m1 = self._get_first_obj(self.clients.get_clients_managed_by(manager_1)).name

        template_m1 = self._get_template_created_by(manager_1)
        # Remove access if present
        template_m1.allowed_clients = [
            x for x in template_m1.allowed_clients if x.notification_client != client_m1]
        template_m1.save(ignore_permissions=True)
        self.assertEqual(template_m1.created_by, manager_1)
        self.assertEqual([
            x for x in template_m1.allowed_clients if x.notification_client == client_m1], [])

        set_active_notification_client(client_m1)
        with self.assertRaises(NotificationTemplateNotFound):
            validate_template_access(template_m1.name)

    def test_subordinate_asking_for_his_own_template(self):
        """
        A normal subordinate client asking for a template he made
        """
        manager_1 = self.clients.get_manager_client().name
        client_m1 = self._get_first_obj(self.clients.get_clients_managed_by(manager_1)).name

        template_c1 = self._get_template_created_by(client_m1)

        set_active_notification_client(client_m1)
        validate_template_access(template_c1.name)

    def test_subordinate_asking_for_colleague_subordinate_template(self):
        """
        A subordinate asking for a template created by his colleague subordinate
        (under same manager)
        Permission will be denied
        """
        manager_1 = self.clients.get_manager_client().name
        clients_m1 = self.clients.get_clients_managed_by(manager_1)
        self.assertGreater(len(clients_m1), 1)

        client_m1 = clients_m1[0].name
        client_m2 = clients_m1[1].name

        template_c1 = self._get_template_created_by(client_m1)

        set_active_notification_client(client_m2)
        with self.assertRaises(NotificationTemplateNotFound):
            validate_template_access(template_c1.name)

    def _get_template_created_by(self, client: str) -> NotificationTemplate:
        """
        Pass in a Client Name and get back a Template
        We handle the rest for you
        """
        templates = self.templates.get_templates_created_by(client)
        if len(templates):
            return templates[0]

        # Hm, we have to create new!
        d = frappe.get_doc(dict(
            doctype="Notification Template",
            created_by=client,
            key=f"RANDOM_TEMPLATE_{frappe.mock('random_int')}",
            subject=frappe.mock("first_name"),
            content=frappe.mock("last_name")
        ))
        d.insert(ignore_permissions=True)
        self.templates.add_document(d)

        return d

    def _get_first_obj(self, iterable: Iterable, default: Optional[Any] = frappe._dict()) -> dict():
        """
        Similar to _get_first but returns a frappe._dict() by default
        """
        return self._get_first(iterable, default)

    def _get_first(self, iterable: Iterable, default: Optional[Any] = None) -> Any:
        """
        Get first element of iterable, return default if list is empty
        """
        return next(iter(iterable), default)
