from unittest import TestCase
from faker import Faker

import frappe
from frappe_notification import (
    InvalidRequest,
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
    _USER_ID_1 = "user-id-1"
    _USER_ID_2 = "user-id-2"
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
                    channel_id=cls.SMS_1, user_identifier=cls._USER_ID_1),
                dict(
                    channel=cls.channels.get_channel("SMS"),
                    channel_id=cls.SMS_2, user_identifier=cls._USER_ID_2),
                dict(
                    channel=cls.channels.get_channel("EMail"),
                    channel_id=cls.EMAIL_1, user_identifier=cls._USER_ID_1),
                dict(
                    channel=cls.channels.get_channel("EMail"),
                    channel_id=cls.EMAIL_2, user_identifier=cls._USER_ID_2),
            ]))
        return d

    def test_channel_filters(self):
        sms_channel = self.channels.get_channel("sms")
        r = get_notification_logs(
            channel=sms_channel,
            channel_id=self.SMS_1,
        )

        self.assertIsInstance(r, list)
        self.assertGreater(len(r), 0)
        self.assertCountEqual([
            "subject", "content", "outbox", "outbox_recipient_row", "time_sent",
            "user_identifier", "seen", "channel", "channel_id"],
            r[0].keys())
        for log in r:
            self.assertEqual(
                frappe.db.get_value(
                    "Notification Outbox Recipient Item",
                    log.outbox_recipient_row,
                    ("channel",
                     "channel_id")),
                (sms_channel, self.SMS_1)
            )

    def test_user_identifier_with_channel_filter(self):
        """
        Combine user_identifier and channel filter
        """
        sms_channel = self.channels.get_channel("sms")
        r = get_notification_logs(
            channel=sms_channel,
            user_identifier=self._USER_ID_1
        )

        for log in r:
            # SMS_1 belongs to _USER_ID_1
            self.assertEqual(
                frappe.db.get_value(
                    "Notification Outbox Recipient Item",
                    log.outbox_recipient_row,
                    ("channel",
                     "channel_id")),
                (sms_channel, self.SMS_1)
            )

            self.assertEqual(log.user_identifier, self._USER_ID_1)

    def test_user_identifier_without_channel_filter(self):
        """
        It is possible to define just user_identifier for a filter
        In such cases, logs across all channels are to be returned

        In this TestSuite, we have used SMS_1 & EMAIL_1 only for USER_ID_1
        """
        r = get_notification_logs(user_identifier=self._USER_ID_1)
        self.assertCountEqual(
            [self.SMS_1, self.EMAIL_1],
            list(set(x.channel_id for x in r))
        )

    def test_limits(self):
        sms_channel = self.channels.get_channel("sms")
        r = get_notification_logs(
            channel=sms_channel,
            channel_id=self.SMS_1,
            limit_page_length=2
        )

        self.assertEqual(len(r), 2)

    def test_get_logs_with_no_or_partial_args(self):
        """
        get_logs accepts:
        - channel & channel_id
        - user_identifier

        it should raise when none of the above are provided
        """

        with self.assertRaises(InvalidRequest):
            get_notification_logs()

        with self.assertRaises(InvalidRequest):
            get_notification_logs(channel="Email")

        with self.assertRaises(InvalidRequest):
            get_notification_logs(channel_id="test@example.com")
