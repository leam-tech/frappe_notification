# Copyright (c) 2022, Leam Technology Systems and Contributors
# See license.txt

# import frappe
import unittest
from faker import Faker

from frappe_testing import TestFixture
from frappe_notification import (
    NotificationClient,
    NotificationClientFixtures,
    NotificationClientNotFound,
    set_active_notification_client)

from .notification_template import (
    NotificationTemplate,
    AllowedClientNotManagedByManager,
    OnlyManagerTemplatesCanBeShared)


class NotificationTemplateFixtures(TestFixture):

    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "Notification Template"
        self.dependent_fixtures = [NotificationClientFixtures]

    def make_fixtures(self):
        clients: NotificationClientFixtures = self.get_dependent_fixture_instance(
            "Notification Client")

        managers = [x for x in clients if x.is_client_manager]
        for manager in managers:
            self.make_otp_template(manager, clients)
            self.make_welcome_template(manager, clients)

    def make_otp_template(
            self, manager: NotificationClient, clients: NotificationClientFixtures):

        managed_clients = clients.get_clients_managed_by(manager.name)

        t = NotificationTemplate(dict(
            doctype="Notification Template",
            title="OTP Template",
            subject="This is your OTP: {{ otp }}",
            content="OTP For Life!",
            created_by=manager.name,
            allowed_clients=[
                dict(notification_client=x.name)
                for x in managed_clients
            ]
        ))
        self.add_document(t.insert())

    def make_welcome_template(
            self, manager: NotificationClient,
            clients: NotificationClientFixtures):
        pass


class TestNotificationTemplate(unittest.TestCase):
    clients = NotificationClientFixtures()
    templates = NotificationTemplateFixtures()
    faker = Faker()

    @classmethod
    def setUpClass(cls):
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()

    def setUp(self):
        self.templates.setUp()

    def tearDown(self) -> None:
        set_active_notification_client(None)
        self.templates.tearDown()

    def test_created_by(self):
        client = self.clients.get_non_manager_client()

        # When no active client is available, result should be None
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),))
        with self.assertRaises(NotificationClientNotFound):
            d.insert()

        # Should go smooth
        set_active_notification_client(client.name)
        self.templates.add_document(d.insert())
        self.assertEqual(d.created_by, client.name)

    def test_set_allowed_clients_on_non_manager_template(self):
        """
        Let's try setting Template.allowed_clients[] on a template created by a non-manager
        """
        client = self.clients.get_non_manager_client()
        set_active_notification_client(client.name)

        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            allowed_clients=[
                dict(notification_client=self.clients.get_non_manager_client().name)
            ]))

        with self.assertRaises(OnlyManagerTemplatesCanBeShared):
            d.insert()

    def test_set_allowed_client_on_non_managed_client(self):
        manager = self.clients.get_manager_client()
        client = None
        while (client is None or client.managed_by == manager.name):
            client = self.clients.get_non_manager_client()

        set_active_notification_client(manager.name)
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            allowed_clients=[
                dict(notification_client=client.name)
            ]))

        with self.assertRaises(AllowedClientNotManagedByManager):
            d.insert()
