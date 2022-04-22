# Copyright (c) 2022, Leam Technology Systems and Contributors
# See license.txt

import unittest
from unittest.mock import MagicMock, patch
from faker import Faker

import frappe
from frappe_notification.utils.exceptions import FrappeNotificationException
from frappe_testing import TestFixture

from frappe_notification import (
    NotificationClientFixtures,
    NotificationChannelFixtures,
    NotificationChannelNotFound,
    NotificationChannelHandlerNotFound,
    NotificationChannelDisabled,
    RecipientErrors
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

    VALID_MOBILE_NO = "+966560440266"
    INVALID_MOBILE_NO_1 = "+966560440299"
    INVALID_MOBILE_NO_2 = "+966560440200"
    NUMBER_VERIFICATIONS = dict({
        VALID_MOBILE_NO: None,
        INVALID_MOBILE_NO_1: FrappeNotificationException(
            error_code="INVALID_MOBILE_NO_1",
            message="Number provided is invalid",
            data=dict()
        ),
        INVALID_MOBILE_NO_2: Exception("Random Error Occurred")
    })

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
        # email_channel = self.channels.get_channel("email")

        def _dummy_handler(*args, **kwargs): None

        # Test normal handler
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = self._get_hooks_notification_handler(
                sms_handler=_dummy_handler)
            _handler = d.get_channel_handler(sms_channel)
        self.assertEqual(_handler, _dummy_handler)

        # Test str-method
        d._channel_handlers = dict()  # clear
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = self._get_hooks_notification_handler(
                sms_handler="frappe.handler.ping")
            _handler = d.get_channel_handler(sms_channel)
        from frappe.handler import ping
        self.assertEqual(_handler, ping)

        # Test Non-Existing Channel
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = self._get_hooks_notification_handler()
            _handler = d.get_channel_handler("non-existent-channel")
        self.assertIsInstance(_handler, NotificationChannelNotFound)

        # Test Undefined Handler
        d._channel_handlers = dict()  # clear
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = self._get_hooks_notification_handler()
            _handler = d.get_channel_handler(sms_channel)
        self.assertIsInstance(_handler, NotificationChannelHandlerNotFound)

        # Test Disabled Channel
        frappe.db.set_value("Notification Channel", sms_channel, "enabled", 0)
        d._channel_handlers = dict()  # clear
        with patch("frappe.get_hooks", spec=True) as mock_get_hooks:
            mock_get_hooks.side_effect = self._get_hooks_notification_handler(
                sms_handler=_dummy_handler)
            _handler = d.get_channel_handler(sms_channel)
        self.assertIsInstance(_handler, NotificationChannelDisabled)
        frappe.db.set_value("Notification Channel", sms_channel, "enabled", 1)

    def test_validate_recipient_channel_ids(self):
        """
        - Let's test the response of validation based on handler behavior
        """
        sms_channel = self.channels.get_channel("sms")

        d = self.get_draft_outbox()
        d.name = "test-outbox-1"
        d.recipients[0].name = "test-outbox-row-1"

        sms_handler = self.get_sms_handler()
        d._channel_handlers[sms_channel] = sms_handler

        # Test valid number
        d.recipients = [[x for x in d.recipients if x.channel == sms_channel][0]]
        d.validate_recipient_channel_ids()
        sms_handler.assert_called_once_with(
            channel=sms_channel,
            channel_id=d.recipients[0].channel_id,
            content=d.content,
            subject=d.subject,
            to_validate=True,
            sender_type=d.recipients[0].sender_type,
            sender=d.recipients[0].sender,
            outbox=d.name,
            outbox_row_name=d.recipients[0].name)

        # Test invalid number
        d.recipients[0].channel_id = self.INVALID_MOBILE_NO_1
        with self.assertRaises(RecipientErrors) as r:
            d.validate_recipient_channel_ids()

        exc = r.exception
        # Asserting some complex flow of error codes 👀
        self.assertEqual(exc.data.recipient_errors[0].error_code,
                         self.NUMBER_VERIFICATIONS[self.INVALID_MOBILE_NO_1].error_code)

        # Test invalid number with random-error
        d.recipients[0].channel_id = self.INVALID_MOBILE_NO_2
        with self.assertRaises(RecipientErrors) as r:
            d.validate_recipient_channel_ids()
        exc = r.exception
        self.assertEqual(exc.data.recipient_errors[0].error_code,
                         "UNKNOWN_ERROR")

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

    def get_sms_handler(self) -> MagicMock:
        sms_handler = MagicMock()

        def _inner(*args, **kwargs):
            channel_id = kwargs.get("channel_id")
            v = self.NUMBER_VERIFICATIONS.get(channel_id)
            if isinstance(v, Exception):
                raise v

        sms_handler.side_effect = _inner
        return sms_handler

    def _get_hooks_notification_handler(self, sms_handler=None, email_handler=None):
        sms_channel = self.channels.get_channel("sms")
        email_channel = self.channels.get_channel("email")

        def _inner(hook, *args, **kwargs):
            if hook == HOOK_NOTIFICATION_CHANNEL_HANDLER:
                return dict({
                    sms_channel: sms_handler,
                    email_channel: email_handler
                })
            else:
                return dict()

        return _inner
