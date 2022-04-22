# Copyright (c) 2022, Leam Technology Systems and Contributors
# See license.txt

import unittest
from unittest.mock import patch
from faker import Faker

import frappe
from frappe_testing import TestFixture

from frappe_notification import (
    NotificationClientFixtures,
    NotificationChannelFixtures,
    NotificationChannelNotFound,
    NotificationChannelHandlerNotFound,
    NotificationChannelDisabled,
)

from .notification_outbox import (NotificationOutbox, HOOK_NOTIFICATION_CHANNEL_HANDLER)


class NotificationOutboxFixtures(TestFixture):
    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "Notification Outbox"

    def make_fixtures(self):
        pass


class TestNotificationOutbox(unittest.TestCase):

    faker = Faker()
    outboxes = NotificationOutboxFixtures()
    clients = NotificationClientFixtures()
    channels = NotificationChannelFixtures()

    @classmethod
    def setUpClass(cls):
        cls.channels.setUp()
        cls.clients.setUp()

    def setUp(self):
        self.outboxes.setUp()

    def tearDown(self) -> None:
        self.outboxes.tearDown()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()
        cls.channels.tearDown()

    def test_create_draft(self):
        """
        A draft Outbox can be created anytime!
        With no consequences. Its only when you submit them the notifications are sent!
        """
        d = self.get_draft_outbox()
        d.insert()
        self.outboxes.add_document(d)

        self.assertFalse(d.is_new())

    def test_get_channel_handler(self):
        """
        - Test the handler returned for channel
        - Test when channel do not exist
        - Test when channel is disabled
        """
        d = self.get_draft_outbox()

        sms_channel = self.channels.get_channel("sms")
        email_channel = self.channels.get_channel("email")

        def _dummy_handler(*args, **kwargs): None

        def _get_hooks(sms_handler=None, email_handler=None):
            def _inner(hook, *args, **kwargs):
                if hook == HOOK_NOTIFICATION_CHANNEL_HANDLER:
                    return dict({
                        sms_channel: sms_handler,
                        email_channel: email_handler
                    })
                else:
                    return dict()

            return _inner

        # Test normal handler
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = _get_hooks(sms_handler=_dummy_handler)
            _handler = d.get_channel_handler(sms_channel)
        self.assertEqual(_handler, _dummy_handler)

        # Test str-method
        d._channel_handlers = dict()  # clear
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = _get_hooks(sms_handler="frappe.handler.ping")
            _handler = d.get_channel_handler(sms_channel)
        from frappe.handler import ping
        self.assertEqual(_handler, ping)

        # Test Non-Existing Channel
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = _get_hooks()
            _handler = d.get_channel_handler("non-existent-channel")
        self.assertIsInstance(_handler, NotificationChannelNotFound)

        # Test Undefined Handler
        d._channel_handlers = dict()  # clear
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = _get_hooks()
            _handler = d.get_channel_handler(sms_channel)
        self.assertIsInstance(_handler, NotificationChannelHandlerNotFound)

        # Test Disabled Channel
        frappe.db.set_value("Notification Channel", sms_channel, "enabled", 0)
        d._channel_handlers = dict()  # clear
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = _get_hooks(sms_handler=_dummy_handler)
            _handler = d.get_channel_handler(sms_channel)
        self.assertIsInstance(_handler, NotificationChannelDisabled)
        frappe.db.set_value("Notification Channel", sms_channel, "enabled", 1)

    def get_draft_outbox(self):
        d = NotificationOutbox(dict(
            doctype="Notification Outbox",
            notification_client=self.clients.get_non_manager_client().name,
            subject=self.faker.first_name(),
            content=self.faker.last_name(),
            recipients=[
                dict(
                    channel=self.channels.get_channel("SMS"),
                    channel_id="+966 560440266"),
                dict(
                    channel=self.channels.get_channel("SMS"),
                    channel_id="+966 560440267"),
                dict(
                    channel=self.channels.get_channel("EMail"),
                    channel_id="test1@notifications.com"),
                dict(
                    channel=self.channels.get_channel("EMail"),
                    channel_id="test2@notifications.com"),
            ]))
        return d
