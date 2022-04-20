# Copyright (c) 2022, Leam Technology Systems and Contributors
# See license.txt

import unittest
from faker import Faker

import frappe
from frappe_testing import TestFixture

from .notification_client import NotificationClient, InvalidManagerClient, CannotDemoteManager


class NotificationClientFixtures(TestFixture):
    faker = Faker()

    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "Notification Client"

    def make_fixtures(self):
        client_managers = ["ABC", "XYZ"]
        clients = ["A", "B", "C"]

        for i in range(len(client_managers)):
            manager = frappe.new_doc("Notification Client")
            manager.update(dict(
                is_client_manager=1,
                title=client_managers[i],
                url=self.faker.url(),
            ))
            manager.insert()
            self.add_document(manager)

            for j in range(len(clients)):
                client = frappe.new_doc("Notification Client")
                client.update(dict(
                    managed_by=manager.name,
                    title=clients[j],
                    url=self.faker.url(),
                ))
                client.insert()
                self.add_document(client)

    def get_manager_client(self):
        import random
        return random.choice([x for x in self if x.is_client_manager])

    def get_clients_managed_by(self, client_manager: str):
        return [x for x in self if x.managed_by == client_manager]

    def get_non_manager_client(self):
        import random
        return random.choice([x for x in self if x.managed_by is not None])


class TestNotificationClient(unittest.TestCase):
    faker = Faker()
    clients = NotificationClientFixtures()

    def setUp(self):
        self.clients.setUp()

    def tearDown(self) -> None:
        self.clients.tearDown()

    def test_api_keys(self):
        d = frappe.new_doc("Notification Client")
        d.update(dict(
            title=self.faker.first_name(),
            url=self.faker.url()
        ))
        d.insert()
        self.clients.add_document(d)

        self.assertIsNotNone(d.api_key)
        self.assertIsNotNone(d.api_secret)

    def test_generate_secret_key(self):
        client: NotificationClient = self.clients[0]

        original_api_secret = client.get_password("api_secret")
        self.assertIsNotNone(original_api_secret)

        client.generate_new_secret()

        new_api_secret = client.get_password("api_secret")
        self.assertIsNotNone(new_api_secret)
        self.assertEqual(len(new_api_secret), client.LEN_API_SECRET)

        self.assertNotEqual(original_api_secret, new_api_secret)

    def test_set_both_is_manager_and_managed_by(self):
        d = frappe.new_doc("Notification Client")
        d.update(dict(
            title=self.faker.first_name(),
            url=self.faker.url(),
            managed_by=self.clients.get_manager_client().name,
            is_client_manager=1
        ))
        d.insert()
        self.clients.add_document(d)

        self.assertEqual(d.managed_by, None)

    def test_set_proper_manager(self):
        d = frappe.new_doc("Notification Client")
        d.update(dict(
            title=self.faker.first_name(),
            url=self.faker.url(),
            managed_by=self.clients.get_manager_client().name,
            is_client_manager=0
        ))
        d.insert()
        self.clients.add_document(d)

        self.assertIsNotNone(d.managed_by)
        self.assertTrue(frappe.db.exists("Notification Client", d.managed_by))
        self.assertEqual(frappe.db.get_value(
            "Notification Client", d.managed_by, "is_client_manager"), 1)

    def test_set_invalid_manager(self):
        d = frappe.new_doc("Notification Client")
        d.update(dict(
            title=self.faker.first_name(),
            url=self.faker.url(),
            managed_by=self.clients.get_non_manager_client().name,
            is_client_manager=0
        ))

        with self.assertRaises(InvalidManagerClient):
            d.insert()

    def test_valid_demotion(self):
        d = frappe.new_doc("Notification Client")
        d.update(dict(
            title=self.faker.first_name(),
            url=self.faker.url(),
            is_client_manager=1
        ))
        d.insert()
        self.clients.add_document(d)

        d.is_client_manager = 0
        d.save()

    def test_invalid_demotion(self):
        d = self.clients.get_manager_client()
        self.assertGreater(len(frappe.get_all("Notification Client", {"managed_by": d.name})), 0)

        d.is_client_manager = 0
        with self.assertRaises(CannotDemoteManager):
            d.save()
