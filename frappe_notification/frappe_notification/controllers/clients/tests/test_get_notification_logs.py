from unittest import TestCase
from faker import Faker

import frappe
from frappe_notification import (
    NotificationChannelFixtures,
    NotificationClientFixtures,
    NotificationOutbox, NotificationOutboxFixtures,
    set_active_notification_client)

from ..get_notification_logs import get_notification_logs


class TestGetNotificationLogs(TestCase):
    faker = Faker()
    channels = NotificationChannelFixtures()
    clients = NotificationClientFixtures()
    outboxes = NotificationOutboxFixtures()

    N_FIXTURE_OUTBOXES = 5
    CLIENT: str = None
    SMS_1 = "+966 560440266"
    SMS_2 = "+966 560440267"
    EMAIL_1 = "test1@notifications.com"
    EMAIL_2 = "test2@notifications.com"

    @classmethod
    def setUpClass(cls):
        cls.channels.setUp()
        cls.clients.setUp()
        cls.outboxes.setUp()

        cls.CLIENT = cls.clients.get_non_manager_client().name
        cls.make_bunch_of_outboxes()
        set_active_notification_client(cls.CLIENT)
        frappe.set_user("Guest")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        set_active_notification_client(None)

        cls.outboxes.tearDown()
        cls.clients.tearDown()
        cls.channels.tearDown()

    @classmethod
    def make_bunch_of_outboxes(cls):
        for i in range(cls.N_FIXTURE_OUTBOXES):
            d = cls.get_draft_outbox()
            d.insert()
            cls.outboxes.add_document(d)

            # Manual submit
            d.db_set("docstatus", 1)
            for r in d.recipients:
                r.db_set("status", "Success")
                r.db_set("time_sent", cls.faker.date_time_this_month())

    @classmethod
    def get_draft_outbox(cls):
        d = NotificationOutbox(dict(
            doctype="Notification Outbox",
            notification_client=cls.CLIENT,
            subject=cls.faker.first_name(),
            content=cls.faker.last_name(),
            recipients=[
                dict(
                    channel=cls.channels.get_channel("SMS"),
                    channel_id=cls.SMS_1),
                dict(
                    channel=cls.channels.get_channel("SMS"),
                    channel_id=cls.SMS_2),
                dict(
                    channel=cls.channels.get_channel("EMail"),
                    channel_id=cls.EMAIL_1),
                dict(
                    channel=cls.channels.get_channel("EMail"),
                    channel_id=cls.EMAIL_2),
            ]))
        return d

    def test_simple(self):
        sms_channel = self.channels.get_channel("sms")
        r = get_notification_logs(
            channel=sms_channel,
            channel_id=self.SMS_1,
        )

        self.assertIsInstance(r, list)
        self.assertGreater(len(r), 0)
        self.assertCountEqual(
            ["subject", "content", "outbox", "outbox_recipient_row", "time_sent"],
            r[0].keys()
        )
        for log in r:
            self.assertEqual(
                frappe.db.get_value(
                    "Notification Outbox Recipient Item",
                    log.outbox_recipient_row,
                    ("channel",
                     "channel_id")),
                (sms_channel, self.SMS_1)
            )

    def test_limits(self):
        sms_channel = self.channels.get_channel("sms")
        r = get_notification_logs(
            channel=sms_channel,
            channel_id=self.SMS_1,
            limit_page_length=2
        )

        self.assertEqual(len(r), 2)
