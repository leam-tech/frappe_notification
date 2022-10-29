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
    RecipientsBatch,
    NotificationOutboxStatus,
    _get_channel_handler_invoke_params,
    HOOK_NOTIFICATION_CHANNEL_HANDLER)


class NotificationOutboxFixtures(TestFixture):
    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "Notification Outbox"

    def make_fixtures(self):
        pass


class TestNotificationOutbox(unittest.TestCase):

    faker = Faker()
    outboxes: NotificationOutboxFixtures = None
    channels: NotificationChannelFixtures = None
    clients: NotificationClientFixtures = None

    VALID_MOBILE_NO = "+966560440266"
    INVALID_MOBILE_NO_1 = "+966560440299"
    INVALID_MOBILE_NO_2 = "+966560440200"
    CHANNEL_VERIFICATIONS = dict()

    VALID_EMAIL_ID = "test1@notifications.com"

    @classmethod
    def setUpClass(cls):
        cls.outboxes = NotificationOutboxFixtures()
        cls.channels = NotificationChannelFixtures()
        cls.clients = NotificationClientFixtures()

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

        cls.CHANNEL_VERIFICATIONS[cls.channels.get_channel("FCM")] = dict()

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
        d._channel_handlers = dict()

        d.name = "test-outbox-1"
        d.recipients[0].name = "test-outbox-row-1"

        sms_handler = self.get_channel_handler(sms_channel)
        d._channel_handlers[sms_channel] = sms_handler

        # - Test valid number
        d.recipients = [[x for x in d.recipients if x.channel == sms_channel][0]]
        d.validate_recipient_channel_ids()
        params = _get_channel_handler_invoke_params(d, d.recipients[0])
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

    def test_recipients_batching_simple(self):
        """
        Simple Recipients batching where 4 FCM Token gets batched as one
        """
        d = self.get_draft_outbox()
        d.recipients = []
        for i in range(4):
            d.append("recipients", dict(
                channel=self.channels.get_channel("FCM"),
                channel_id="random-token-{}".format(i),
                user_identifier="user-{}".format(0 if i < 2 else 1),
            ))

        batched_recipients = d.get_batched_recipients()
        self.assertEqual(len(batched_recipients), 1)
        self.assertIsInstance(batched_recipients[0], RecipientsBatch)

        batch = batched_recipients[0]
        self.assertEqual(batch.channel, self.channels.get_channel("FCM"))
        self.assertEqual(batch.channel_args, None)
        self.assertTrue("user-0" in batch.channel_ids)
        self.assertTrue("user-1" in batch.channel_ids)
        self.assertCountEqual(batch.channel_ids["user-0"], ['random-token-0', 'random-token-1'])
        self.assertCountEqual(batch.channel_ids["user-1"], ['random-token-2', 'random-token-3'])

    def test_recipients_batching_mixed(self):
        """
        A mix of recipients happen when there are
        batched & non-batched recipients in a single outbox
        """
        # Draft outbox already has SMS & Email recipients
        d = self.get_draft_outbox()
        num_non_batched = len(d.recipients)

        # Lets add a couple of FCM Recipients (Batched)
        for i in range(4):
            d.append("recipients", dict(
                channel=self.channels.get_channel("FCM"),
                channel_id="random-token-{}".format(i),
                user_identifier="user-{}".format(0 if i < 2 else 1),
            ))

        recipients = d.get_batched_recipients()
        self.assertEqual(len(recipients), num_non_batched + 1)
        for idx, r in enumerate(recipients):
            if idx < num_non_batched:
                self.assertIsInstance(r, NotificationOutboxRecipientItem)
            else:
                self.assertIsInstance(r, RecipientsBatch)

    def test_send_notifications_simple(self):
        """
        - Lets try sending out two Notifications, 1 SMS & 1 Email
        """
        d = self.get_draft_outbox()
        d._channel_handlers = dict()

        d.recipients = []
        d.append("recipients", dict(
            status=NotificationOutboxStatus.PENDING.value,
            channel=self.channels.get_channel("SMS"),
            channel_id="+966 560440266"))
        d.append("recipients", dict(
            status=NotificationOutboxStatus.PENDING.value,
            channel=self.channels.get_channel("Email"),
            channel_id="test!notifications.com"))

        invoke_params_0 = _get_channel_handler_invoke_params(d, d.recipients[0])
        invoke_params_1 = _get_channel_handler_invoke_params(d, d.recipients[1])

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

    def test_send_notifications_batched(self):
        """
        Lets try sending notification to 4 FCM Tokens
        """
        d = self.get_draft_outbox()
        d._channel_handlers = dict()

        d.recipients = []
        for i in range(4):
            d.append("recipients", dict(
                channel=self.channels.get_channel("FCM"),
                channel_id="random-token-{}".format(i),
                user_identifier="user-{}".format(0 if i < 2 else 1),
            ))

        _invoke_params = _get_channel_handler_invoke_params(d, d.get_batched_recipients()[0])

        fcm_channel = self.channels.get_channel("FCM")
        fcm_handler = self.get_channel_handler(fcm_channel)
        fcm_handler.fnargs = _invoke_params.keys()  # Please check frappe.call() implementation

        d._channel_handlers[fcm_channel] = fcm_handler

        d.before_submit()
        d.send_pending_notifications()

        fcm_handler.assert_called_once_with(**_invoke_params)

    def test_send_notifications_batched_mixed(self):
        """
        Send to SMS and FCM
        """
        d = self.get_draft_outbox()
        d._channel_handlers = dict()

        # Only SMS Recipients
        d.recipients = [x for x in d.recipients if x.channel == self.channels.get_channel("SMS")]
        self.assertTrue(len(d.recipients) > 0)

        for i in range(4):
            d.append("recipients", dict(
                channel=self.channels.get_channel("FCM"),
                channel_id="random-token-{}".format(i),
                user_identifier="user-{}".format(0 if i < 2 else 1),
            ))

        fcm_invoke_params = _get_channel_handler_invoke_params(d, d.get_batched_recipients()[-1])
        sms_invoke_params = _get_channel_handler_invoke_params(d, d.recipients[0])

        sms_channel = self.channels.get_channel("SMS")
        sms_handler = self.get_channel_handler(sms_channel)
        sms_handler.fnargs = sms_invoke_params.keys()  # Please check frappe.call() implementation

        fcm_channel = self.channels.get_channel("FCM")
        fcm_handler = self.get_channel_handler(fcm_channel)
        fcm_handler.fnargs = fcm_invoke_params.keys()  # Please check frappe.call() implementation

        d._channel_handlers[sms_channel] = sms_handler
        d._channel_handlers[fcm_channel] = fcm_handler

        d.before_submit()
        d.send_pending_notifications()

        self.assertEqual(sms_handler.call_count, len([x for x in d.recipients if x.channel == self.channels.get_channel("SMS")]))  # noqa
        fcm_handler.assert_called_once()

    def test_update_recipient_status(self):
        d = self.get_draft_outbox()
        d.before_submit()
        d.insert()
        self.addCleanup(lambda: d.cancel() and d.delete())

        d.db_set("docstatus", 1)

        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.PENDING)
        for row in d.recipients:
            self.assertEqual(NotificationOutboxStatus(row.status), NotificationOutboxStatus.PENDING)

        # Update status of non-existent row
        d.update_recipient_status(dict(random_row=NotificationOutboxStatus.FAILED))
        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.PENDING)

        # Update status of all rows as success
        d.update_recipient_status({
            r.name: NotificationOutboxStatus.SUCCESS
            for r in d.recipients
        })
        self.assertTrue(all(r.time_sent for r in d.recipients))

        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.SUCCESS)

        # Update status of all rows as Failure
        d.update_recipient_status({
            r.name: NotificationOutboxStatus.FAILED
            for r in d.recipients
        })

        self.assertEqual(NotificationOutboxStatus(d.status), NotificationOutboxStatus.FAILED)

        # Update one row to be successful
        d.update_recipient_status({d.recipients[0].name: NotificationOutboxStatus.SUCCESS})
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
