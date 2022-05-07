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

from .notification_outbox import (
    NotificationOutbox,
    NotificationOutboxRecipientItem,
    ChannelHandlerInvokeParams,
    NotificationOutboxStatus,
    HOOK_NOTIFICATION_CHANNEL_HANDLER)


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
    CHANNEL_VERIFICATIONS = dict()

    VALID_EMAIL_ID = "test1@notifications.com"

    @classmethod
    def setUpClass(cls):
        cls.channels.setUp()
        cls.clients.setUp()

        cls.CHANNEL_VERIFICATIONS[cls.channels.get_channel("SMS")] = dict({
            cls.VALID_MOBILE_NO: None,
            cls.INVALID_MOBILE_NO_1: FrappeNotificationException(
                error_code="INVALID_MOBILE_NO_1",
                message="Number provided is invalid",
                data=dict()
            ),
            cls.INVALID_MOBILE_NO_2: Exception("Random Error Occurred")
        })

        cls.CHANNEL_VERIFICATIONS[cls.channels.get_channel("Email")] = dict({
            cls.VALID_EMAIL_ID: None
        })

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

        sms_handler = self.get_channel_handler(sms_channel)
        d._channel_handlers[sms_channel] = sms_handler

        # - Test valid number
        d.recipients = [[x for x in d.recipients if x.channel == sms_channel][0]]
        d.validate_recipient_channel_ids()
        params = self._get_channel_handler_invoke_params(d, d.recipients[0])
        params.to_validate = True
        sms_handler.assert_called_once_with(**params)

        # - Test invalid number
        d.recipients[0].channel_id = self.INVALID_MOBILE_NO_1
        with self.assertRaises(RecipientErrors) as r:
            d.validate_recipient_channel_ids()

        exc = r.exception
        #       Asserting some complex flow of error codes 👀
        self.assertEqual(exc.data.recipient_errors[0].error_code,
                         self.CHANNEL_VERIFICATIONS[sms_channel].get(
                             self.INVALID_MOBILE_NO_1).error_code)

        # - Test invalid number with random-error
        d.recipients[0].channel_id = self.INVALID_MOBILE_NO_2
        with self.assertRaises(RecipientErrors) as r:
            d.validate_recipient_channel_ids()
        exc = r.exception
        self.assertEqual(exc.data.recipient_errors[0].error_code,
                         "UNKNOWN_ERROR")

    def test_send_notifications_1(self):
        """
        - Lets try sending out two Notifications, 1 SMS & 1 Email
        """
        d = self.get_draft_outbox()
        d.recipients = []
        d.append("recipients", dict(
            status=NotificationOutboxStatus.PENDING.value,
            channel=self.channels.get_channel("SMS"),
            channel_id="+966 560440266"))
        d.append("recipients", dict(
            status=NotificationOutboxStatus.PENDING.value,
            channel=self.channels.get_channel("Email"),
            channel_id="test!notifications.com"))

        invoke_params_0 = self._get_channel_handler_invoke_params(d, d.recipients[0])
        invoke_params_1 = self._get_channel_handler_invoke_params(d, d.recipients[1])

        sms_channel = self.channels.get_channel("SMS")
        sms_handler = self.get_channel_handler(sms_channel)
        sms_handler.fnargs = invoke_params_0.keys()  # Please check frappe.call() implementation

        email_channel = self.channels.get_channel("Email")
        email_handler = self.get_channel_handler(email_channel)
        email_handler.fnargs = invoke_params_1.keys()  # Please check frappe.call() implementation

        d._channel_handlers[sms_channel] = sms_handler
        d._channel_handlers[email_channel] = email_handler

        d.before_submit()
        d.send_pending_notifications()

        sms_handler.assert_called_once_with(**invoke_params_0)
        email_handler.assert_called_once_with(**invoke_params_1)

    def test_update_status(self):
        d = self.get_draft_outbox()
        d.before_submit()
        d.insert()
        self.addCleanup(lambda: d.cancel() and d.delete())

        d.db_set("docstatus", 1)

        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.PENDING)
        for row in d.recipients:
            self.assertEqual(NotificationOutboxStatus(row.status), NotificationOutboxStatus.PENDING)

        # Update status of non-existent row
        d.update_status("random-row", NotificationOutboxStatus.FAILED)
        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.PENDING)

        # Update status of all rows as success
        for row in d.recipients:
            d.update_status(row.name, NotificationOutboxStatus.SUCCESS)

        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.SUCCESS)

        # Update status of all rows as Failure
        for row in d.recipients:
            d.update_status(row.name, NotificationOutboxStatus.FAILED)

        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.FAILED)

        # Update one row to be successfull
        d.update_status(d.recipients[0].name, NotificationOutboxStatus.SUCCESS)
        self.assertEqual(
            NotificationOutboxStatus(d.status), NotificationOutboxStatus.PARTIAL_SUCCESS)

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

    def get_channel_handler(self, channel: str) -> MagicMock:
        channel_handler = MagicMock()

        def _inner(*args, **kwargs):
            channel_id = kwargs.get("channel_id")
            v = self.CHANNEL_VERIFICATIONS.get(channel).get(channel_id)
            if isinstance(v, Exception):
                raise v

        channel_handler.side_effect = _inner
        return channel_handler

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

    def _get_channel_handler_invoke_params(
            self,
            d: NotificationOutbox,
            row: NotificationOutboxRecipientItem):

        return ChannelHandlerInvokeParams(dict(
            channel=row.get("channel"),
            sender=row.get("sender"),
            sender_type=row.get("sender_type"),
            channel_id=row.get("channel_id"),
            subject=d.get("subject"),
            content=d.get("content"),
            to_validate=False,
            outbox=d.name,
            outbox_row_name=row.get("name"),
        ))
