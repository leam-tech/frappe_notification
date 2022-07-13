from unittest import TestCase
from faker import Faker

import frappe
from frappe_notification import (
    NotificationChannelFixtures,
    NotificationClientFixtures,
    NotificationOutboxNotFound,
    NotificationClientNotFound,
    NotificationOutbox, NotificationOutboxFixtures,
    set_active_notification_client)

from ..mark_log_seen import mark_log_seen


# TODO: Add user_identifier, update tests

class TestMarkLogSeen(TestCase):
    faker = Faker()
    channels: NotificationChannelFixtures = None
    clients: NotificationClientFixtures = None
    outboxes: NotificationOutboxFixtures = None

    N_FIXTURE_OUTBOXES = 5
    SMS_1 = "+966 560440266"
    SMS_2 = "+966 560440267"
    EMAIL_1 = "test1@notifications.com"
    EMAIL_2 = "test2@notifications.com"

    @classmethod
    def setUpClass(cls):
        cls.channels = NotificationChannelFixtures()
        cls.clients = NotificationClientFixtures()
        cls.outboxes = NotificationOutboxFixtures()

        cls.channels.setUp()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):

        cls.clients.tearDown()
        cls.channels.tearDown()

    def setUp(self):
        self.outboxes.setUp()
        self.make_bunch_of_outboxes()
        set_active_notification_client(None)
        frappe.set_user("Guest")

    def tearDown(self):
        set_active_notification_client(None)
        frappe.set_user("Administrator")

        self.outboxes.tearDown()

    def make_bunch_of_outboxes(self):
        for i in range(self.N_FIXTURE_OUTBOXES):
            d = self.get_draft_outbox()
            d.insert()
            self.outboxes.add_document(d)

            # Manual submit
            d.db_set("docstatus", 1)
            for r in d.recipients:
                r.db_set("status", "Success")
                r.db_set("time_sent", self.faker.date_time_this_month())

    def get_draft_outbox(self):
        d = NotificationOutbox(dict(
            doctype="Notification Outbox",
            notification_client=self.clients.get_non_manager_client().name,
            subject=self.faker.first_name(),
            content=self.faker.last_name(),
            recipients=[
                dict(
                    channel=self.channels.get_channel("SMS"),
                    channel_id=self.SMS_1, user_identifier="user-id-1"),
                dict(
                    channel=self.channels.get_channel("SMS"),
                    channel_id=self.SMS_2, user_identifier="user-id-2"),
                dict(
                    channel=self.channels.get_channel("EMail"),
                    channel_id=self.EMAIL_1, user_identifier="user-id-3"),
                dict(
                    channel=self.channels.get_channel("EMail"),
                    channel_id=self.EMAIL_2, user_identifier="user-id-4"),
            ]))
        return d

    def test_with_outbox_recipient_row(self):
        """
        Call mark_log_seen(outbox, recipient_row_name)
        It should mark successfully
        """
        outbox: NotificationOutbox = self.outboxes[0]
        set_active_notification_client(outbox.notification_client)

        ROW_IDX = len(outbox.recipients) - 1
        self.assertEqual(outbox.recipients[ROW_IDX].seen, 0)

        t = mark_log_seen(
            outbox=outbox.name,
            outbox_recipient_row=outbox.recipients[ROW_IDX].name,
        )

        self.assertTrue(t)
        outbox.reload()
        self.assertEqual(outbox.recipients[ROW_IDX].seen, 1)

    def test_with_channel_and_channel_id(self):
        """
        Call mark_log_seen(outbox, channel="SMS", channel_id"+966...")
        It should mark successfully
        """

        outbox: NotificationOutbox = self.outboxes[0]
        set_active_notification_client(outbox.notification_client)

        ROW_IDX = len(outbox.recipients) - 1
        _row = outbox.recipients[ROW_IDX]
        self.assertEqual(outbox.recipients[ROW_IDX].seen, 0)

        t = mark_log_seen(
            outbox=outbox.name,
            channel=_row.channel,
            channel_id=_row.channel_id,
        )

        self.assertTrue(t)
        outbox.reload()

        self.assertEqual(outbox.recipients[ROW_IDX].seen, 1)

    def test_with_user_identifier(self):
        """
        Call mark_log_seen(outbox, user_identifier="")
        It should mark successfully
        """

        outbox: NotificationOutbox = self.outboxes[0]
        set_active_notification_client(outbox.notification_client)

        ROW_IDX = len(outbox.recipients) - 1
        _id = outbox.recipients[ROW_IDX].user_identifier
        self.assertEqual(outbox.recipients[ROW_IDX].seen, 0)

        t = mark_log_seen(
            outbox=outbox.name,
            user_identifier=_id
        )

        self.assertTrue(t)
        outbox.reload()

        self.assertEqual(outbox.recipients[ROW_IDX].seen, 1)

    def test_marking_on_an_outbox_belonging_to_some_other_client(self):
        """
        Only the owner client should be able to update seen statuses
        """
        outbox: NotificationOutbox = self.outboxes[0]
        client = outbox.notification_client
        while client == outbox.notification_client:
            client = self.faker.random.choice(self.clients).name

        set_active_notification_client(client)

        with self.assertRaises(NotificationOutboxNotFound):
            mark_log_seen(outbox=outbox.name, outbox_recipient_row=outbox.recipients[0].name)

    def test_marking_on_non_existent_outbox(self):
        """
        Should raise error
        """
        set_active_notification_client(self.clients[0].name)

        with self.assertRaises(NotificationOutboxNotFound):
            mark_log_seen(outbox="random-non-existent", user_identifier="random")

    def test_marking_on_a_non_existent_row_on_valid_outbox(self):
        """
        Even though the outbox is valid
        if recipient refs fails to match, it should throw
        """
        outbox: NotificationOutbox = self.outboxes[0]
        set_active_notification_client(outbox.notification_client)

        with self.assertRaises(NotificationOutboxNotFound):
            mark_log_seen(outbox=outbox.name, user_identifier="random")

        with self.assertRaises(NotificationOutboxNotFound):
            mark_log_seen(outbox=outbox.name, channel="random", channel_id="random-2")

        with self.assertRaises(NotificationOutboxNotFound):
            mark_log_seen(outbox=outbox.name, outbox_recipient_row="random-2")

    def test_non_client(self):
        """
        Should raise
        """
        with self.assertRaises(NotificationClientNotFound):
            mark_log_seen(outbox=self.outboxes[0].name, outbox_recipient_row="random")
