# Copyright (c) 2022, Leam Technology Systems and Contributors
# See license.txt

# import frappe
import unittest
from unittest.mock import patch, MagicMock
from faker import Faker
from typing import List

import frappe
from frappe_testing import TestFixture
from frappe_notification import (
    NotificationClient,
    NotificationOutbox,
    NotificationClientFixtures,
    NotificationChannelFixtures,
    NotificationClientNotFound,
    set_active_notification_client)

from .notification_template import (
    NotificationTemplate,
    AllowedClientNotManagedByManager,
    OnlyManagerTemplatesCanBeShared,
)


class NotificationTemplateFixtures(TestFixture):

    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "Notification Template"
        self.dependent_fixtures = [NotificationClientFixtures]

    def make_fixtures(self):
        clients: NotificationClientFixtures = self.get_dependent_fixture_instance(
            "Notification Client")

        managers = [x for x in clients if x.is_client_manager]
        for manager in managers:
            self.make_otp_template(manager, clients)
            self.make_welcome_template(manager, clients)

    def make_otp_template(
            self, manager: NotificationClient, clients: NotificationClientFixtures):

        managed_clients = clients.get_clients_managed_by(manager.name)

        t = NotificationTemplate(dict(
            doctype="Notification Template",
            title="OTP Template",
            subject="This is your OTP: {{ otp }}",
            content="OTP For Life!",
            created_by=manager.name,
            allowed_clients=[
                dict(notification_client=x.name)
                for x in managed_clients
            ]
        ))
        self.add_document(t.insert())

    def make_welcome_template(
            self, manager: NotificationClient,
            clients: NotificationClientFixtures):
        pass


class TestNotificationTemplate(unittest.TestCase):

    channels = NotificationChannelFixtures()
    clients = NotificationClientFixtures()
    templates = NotificationTemplateFixtures()
    faker = Faker()

    @classmethod
    def setUpClass(cls):
        cls.channels.setUp()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()
        cls.channels.tearDown()

    def setUp(self):
        self.templates.setUp()

    def tearDown(self) -> None:
        set_active_notification_client(None)
        self.templates.tearDown()

    def test_created_by(self):
        client = self.clients.get_non_manager_client()

        # When no active client is available, result should be None
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),))
        with self.assertRaises(NotificationClientNotFound):
            d.insert()

        # Should go smooth
        set_active_notification_client(client.name)
        self.templates.add_document(d.insert())
        self.assertEqual(d.created_by, client.name)

    def test_set_allowed_clients_on_non_manager_template(self):
        """
        Let's try setting Template.allowed_clients[] on a template created by a non-manager
        """
        client = self.clients.get_non_manager_client()
        set_active_notification_client(client.name)

        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            allowed_clients=[
                dict(notification_client=self.clients.get_non_manager_client().name)
            ]))

        with self.assertRaises(OnlyManagerTemplatesCanBeShared):
            d.insert()

    def test_set_allowed_client_on_non_managed_client(self):
        manager = self.clients.get_manager_client()
        client = None
        while (client is None or client.managed_by == manager.name):
            client = self.clients.get_non_manager_client()

        set_active_notification_client(manager.name)
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            allowed_clients=[
                dict(notification_client=client.name)
            ]))

        with self.assertRaises(AllowedClientNotManagedByManager):
            d.insert()

    def test_lang_templates(self):

        PREDEFINED_ROW_COUNT = 1
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            lang="en",
            lang_templates=[
                dict(lang="ar", subject="A", content="B")
            ]))

        # Try setting the same 'en' row
        d.append("lang_templates", dict(lang=d.lang, subject=self.faker.first_name()))
        d.validate_language_templates()
        self.assertEqual(len(d.lang_templates), PREDEFINED_ROW_COUNT)

        # Try add empty content & subject
        d.append("lang_templates", dict(lang="en-US", subject=None))
        d.validate_language_templates()
        self.assertEqual(len(d.lang_templates), PREDEFINED_ROW_COUNT)

        # Try adding duplicate lang
        d.append("lang_templates", dict(lang=d.lang_templates[0].lang, subject="A"))
        d.validate_language_templates()
        self.assertEqual(len(d.lang_templates), PREDEFINED_ROW_COUNT)

    def test_get_channel_sender(self):

        _CHANNEL = self.channels[0].name

        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            lang="en",
            channel_senders=[
                dict(channel=self.channels[-1].name, sender_type="C", sender="D"),
                dict(channel=_CHANNEL, sender_type="A", sender="B"),
            ]))

        sender_type, sender = d.get_channel_sender(_CHANNEL)
        self.assertEqual(sender_type, "A")
        self.assertEqual(sender, "B")

    def test_get_lang_templates(self):
        _lang_templates = frappe._dict({
            "en": ("en-subject!", "en-content!"),
            "ar": ("ar-subject", "ar-content"),
            "es": ("es-subject", "es-content"),
        })

        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            lang="en",
            subject=_lang_templates["en"][0],
            content=_lang_templates["en"][1],
            lang_templates=[
                dict(lang="ar", subject=_lang_templates["ar"][0], content=_lang_templates["ar"][1]),
                dict(lang="es", subject=_lang_templates["es"][0], content=_lang_templates["es"][1]),
            ]))

        self.assertEqual(d.get_lang_templates("en"), _lang_templates["en"])
        self.assertEqual(d.get_lang_templates("ar"), _lang_templates["ar"])
        self.assertEqual(d.get_lang_templates("es"), _lang_templates["es"])

        # Now, for a lang for which template is not defined
        self.assertEqual(d.get_lang_templates("pr"), _lang_templates["en"])

    @patch("frappe.model.document.Document.insert", spec=True)
    def test_send_notification_1(self, mock_insert: MagicMock):
        """
        Let's try sending out a simple OTP Notification to
        - EMail test@test.com
        - SMS +966 560440266
        """
        sms_channel = self.channels.get_channel("SMS")
        sms_receiver_1 = "+966 560440266"
        sms_receiver_2 = "+966 560440262"

        email_channel = self.channels.get_channel("Email")
        email_sender_type = "Email Account"
        email_sender = "test@notifications.com"
        email_receiver_1 = "test1@notifications.com"
        email_receiver_2 = "test2@notifications.com"

        _OTP = "989566"
        _CTX = dict(otp=_OTP)

        d = NotificationTemplate(dict(
            doctype="Notification Template",
            title=self.faker.first_name(),
            lang="en",
            subject="Your Subject OTP is {{otp}}",
            content="Your Content OTP is {{otp}}",
            channel_senders=[
                dict(channel=email_channel, sender_type=email_sender_type, sender=email_sender),
            ]
        ))

        recipient_list = [
            {"channel": sms_channel, "channel_id": sms_receiver_1},
            {"channel": sms_channel, "channel_id": sms_receiver_2},
            {"channel": email_channel, "channel_id": email_receiver_1},
            {"channel": email_channel, "channel_id": email_receiver_2},
        ]

        outbox = d.send_notification(_CTX, recipient_list)
        self.assertIsNotNone(outbox)
        mock_insert.assert_called_once()

        self.assertEqual(len(outbox.recipients), len(recipient_list))
        for i in range(len(recipient_list)):
            outbox_row = outbox.recipients[i]
            recipient = frappe._dict(recipient_list[i])

            self.assertEqual(outbox_row.channel, recipient.channel)
            self.assertEqual(outbox_row.channel_id, recipient.channel_id)

            if recipient.channel == email_channel:
                self.assertEqual(outbox_row.sender_type, email_sender_type)
                self.assertEqual(outbox_row.sender, email_sender)

    @patch("frappe.get_hooks", spec=True)
    def old_send_notification_1(self, mock_get_hooks: MagicMock):
        """
        Let's try sending out a simple OTP Notification to
        - EMail test@test.com
        - SMS +966 560440266
        """
        sms_channel = self.get_channel("SMS")
        sms_receiver_1 = "+966 560440266"
        sms_receiver_2 = "+966 560440262"

        email_channel = self.get_channel("Email")
        email_sender_type = "Email Account"
        email_sender = "test@notifications.com"
        email_receiver_1 = "test1@notifications.com"
        email_receiver_2 = "test2@notifications.com"

        sms_mock = MagicMock()
        email_mock = MagicMock()
        sms_mock.side_effect = _channel_handler
        email_mock.side_effect = _channel_handler

        def _get_hooks(hook, *args, **kwargs):
            if hook == HOOK_NOTIFICATION_CHANNEL_HANDLER:
                return dict({
                    sms_channel: sms_mock,
                    email_channel: email_mock
                })
            else:
                return dict()

        mock_get_hooks.side_effect = _get_hooks

        self.assertIsInstance(status, NotificationStatus)
        self.assertEqual(len(recipient_list), len(status.recipients))

        subject = frappe.render_template(d.subject, _CTX)
        content = frappe.render_template(d.content, _CTX)

        sms_mock.assert_called_once_with(
            channel=sms_channel,
            recipients=[sms_receiver_1, sms_receiver_2],
            subject=subject,
            content=content,
            sender=None,
            sender_type=None
        )

        email_mock.assert_called_once_with(
            channel=email_channel,
            recipients=[email_receiver_1, email_receiver_2],
            subject=subject,
            content=content,
            sender=email_sender,
            sender_type=email_sender_type,
        )

        for i in range(len(recipient_list)):
            recipient = frappe._dict(recipient_list[i])
            recipient_status = status.recipients[i]

            self.assertIsInstance(recipient_status, NotificationRecipientStatus)
            self.assertIsInstance(recipient_status.status, NotificationChannelStatus)
            self.assertEqual(recipient_status.channel, recipient.channel)
            self.assertEqual(recipient_status.channel_id, recipient.channel_id)


def _channel_handler(
        channel: str,
        sender_type: str,
        sender: str,
        subject: str,
        content: str,
        recipients: List[str] = []):

    return NotificationStatus(dict(
        subject=subject,
        content=content,
        recipients=[NotificationRecipientStatus(dict(
            status=NotificationChannelStatus.QUEUED,
            sender_type=sender_type,
            sender=sender,
            channel=channel,
            channel_id=x
        )) for x in recipients]))
