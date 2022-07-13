from frappe_notification.utils.client import set_active_notification_client
from unittest import TestCase

from frappe_notification import (
    NotificationClientFixtures,
    NotificationClientNotFound,
)

from ..get_me import get_me


class TestGetMe(TestCase):
    clients: NotificationClientFixtures = None

    @classmethod
    def setUpClass(cls):
        cls.clients = NotificationClientFixtures()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()

    def test_admin(self):
        with self.assertRaises(NotificationClientNotFound):
            get_me()

    def test_valid(self):
        clients = [self.clients.get_manager_client(), self.clients.get_non_manager_client()]

        for client in clients:
            set_active_notification_client(client.name)

            t = get_me()
            self.assertEqual(client.name, t.notification_client)
            self.assertEqual(client.title, t.title)
            self.assertEqual(client.url, t.url)
            self.assertEqual(client.enabled, t.enabled)
            self.assertEqual(client.is_client_manager, t.is_client_manager)
            self.assertEqual(client.managed_by, t.managed_by)
