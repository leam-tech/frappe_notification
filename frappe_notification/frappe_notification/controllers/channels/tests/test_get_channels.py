from unittest import TestCase

import frappe
from frappe_notification import (
    NotificationChannelFixtures,
    NotificationClientFixtures,
    NotificationClientNotFound,
    set_active_notification_client)

from ..get_channels import get_channels


class TestGetChannels(TestCase):
    channels = NotificationChannelFixtures()
    clients = NotificationClientFixtures()

    @classmethod
    def setUpClass(cls):
        cls.channels.setUp()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()
        cls.channels.tearDown()

    def setUp(self) -> None:
        set_active_notification_client(None)
        frappe.set_user("Guest")

    def tearDown(self):
        set_active_notification_client(None)
        frappe.set_user("Administrator")

    def test_simple(self):
        client = self.clients.get_non_manager_client()
        set_active_notification_client(client.name)

        channels = get_channels()
        self.assertGreater(len(channels), 0)
        for channel in channels:
            self.assertCountEqual(channel.keys(), ["name", "title"])
            self.assertEqual(
                frappe.db.get_value("Notification Channel", channel.name, "enabled"),
                1
            )

    def test_non_client(self):
        with self.assertRaises(NotificationClientNotFound):
            get_channels()
