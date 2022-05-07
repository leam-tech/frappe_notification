# Copyright (c) 2022, Leam Technology Systems and Contributors
# See license.txt

import frappe
import unittest

from frappe_testing import TestFixture


class NotificationChannelFixtures(TestFixture):
    already_existing_channels = []

    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "Notification Channel"

    def tearDown(self):
        # Make sure we do not tamper existing Channel Fixture
        channel_list = self.fixtures[self.DEFAULT_DOCTYPE]
        for i in range(len(channel_list) - 1, -1, -1):
            channel = channel_list[i]
            if channel.name not in self.already_existing_channels:
                continue
            channel_list.remove(channel)

        return super().tearDown()

    def make_fixtures(self):
        channels = ["SMS", "Email", "Whatsapp", "Telegram", "Slack"]
        for channel in channels:
            if frappe.db.exists("Notification Channel", channel):
                channel = frappe.get_doc("Notification Channel", channel)
                self.already_existing_channels.append(channel.name)
            else:
                channel = frappe.get_doc(dict(doctype="Notification Channel", title=channel))
                channel.insert()

            self.add_document(channel)

    def get_channel(self, channel: str):
        channel = next(iter([
            x.name for x in self if x.name.lower() == channel.lower()]), None)
        return channel


class TestNotificationChannel(unittest.TestCase):
    pass
