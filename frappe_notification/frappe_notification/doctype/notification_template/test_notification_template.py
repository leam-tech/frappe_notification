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
    InvalidTemplateForking,
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
            key="OTP Template",
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

    def get_templates_created_by(self, client: str) -> List[NotificationTemplate]:
        return [x for x in self if x.created_by == client]


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
            key=self.faker.first_name(),))
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
            key=self.faker.first_name(),
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
            key=self.faker.first_name(),
            allowed_clients=[
                dict(notification_client=client.name)
            ]))

        with self.assertRaises(AllowedClientNotManagedByManager):
            d.insert()

    def test_lang_templates(self):

        PREDEFINED_ROW_COUNT = 1
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            key=self.faker.first_name(),
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
            key=self.faker.first_name(),
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
            key=self.faker.first_name(),
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
    @patch("frappe.model.document.Document.db_set", spec=True)
    def test_send_notification_1(self, db_set_mock: MagicMock, mock_insert: MagicMock):
        """
        Let's try sending out a simple OTP Notification to
        - EMail test@test.com
        - SMS +966 560440266
        """
        client = self.clients[0].name
        set_active_notification_client(client)

        sms_channel = self.channels.get_channel("SMS")
        sms_receiver_1 = "+966 560440266"
        sms_receiver_2 = "+966 560440262"

        email_channel = self.channels.get_channel("Email")
        email_sender_type = "Email Account"
        email_sender = "test@notifications.com"
        email_receiver_1 = "test1@notifications.com"
        email_receiver_2 = "test2@notifications.com"

        sms_args = dict(sms_type=1)
        sms_args_special = dict(sms_type=2)
        email_args_special = dict(email_type=2)

        _OTP = "989566"
        _CTX = dict(
            otp=_OTP,
            channel_args=frappe.as_json({
                sms_channel: sms_args,
            }))

        d = NotificationTemplate(dict(
            doctype="Notification Template",
            key=self.faker.first_name(),
            lang="en",
            subject="Your Subject OTP is {{otp}}",
            content="Your Content OTP is {{otp}}",
            channel_senders=[
                dict(channel=email_channel, sender_type=email_sender_type, sender=email_sender),
            ]
        ))

        recipient_list = [
            {
                "channel": sms_channel,
                "channel_id": sms_receiver_1,
                "user_identifier": "id-121",
                "channel_args": sms_args_special},  # Dedicated Args
            {
                "channel": sms_channel,
                "channel_id": sms_receiver_2,
                "user_identifier": "id-122"},
            {
                "channel": email_channel,
                "channel_id": email_receiver_1,
                "user_identifier": "id-123",
                "channel_args": email_args_special},  # Dedicated Args
            {
                "channel": email_channel,
                "channel_id": email_receiver_2,
                "user_identifier": "id-124"},
        ]

        outbox: NotificationOutbox = d.send_notification(_CTX, recipient_list)
        self.assertIsNotNone(outbox)
        mock_insert.assert_called_once()

        self.assertEqual(db_set_mock.call_count, 2)
        self.assertIn("last_used_on", [x[0][0] for x in db_set_mock.call_args_list])
        self.assertIn(("last_used_by", client), [x[0] for x in db_set_mock.call_args_list])

        self.assertEqual(len(outbox.recipients), len(recipient_list))
        for i in range(len(recipient_list)):
            outbox_row = outbox.recipients[i]
            recipient = frappe._dict(recipient_list[i])

            self.assertEqual(outbox_row.channel, recipient.channel)
            self.assertEqual(outbox_row.channel_id, recipient.channel_id)
            self.assertEqual(outbox_row.user_identifier, recipient.user_identifier)

            if recipient.channel == email_channel:
                self.assertEqual(outbox_row.sender_type, email_sender_type)
                self.assertEqual(outbox_row.sender, email_sender)

                if recipient.channel_id == email_receiver_1:
                    self.assertIsInstance(outbox_row.channel_args, str)
                    self.assertEqual(frappe.parse_json(outbox_row.channel_args), email_args_special)
                else:
                    self.assertEqual(outbox_row.channel_args, "{}")

            if recipient.channel == sms_channel:
                if recipient.channel_id == sms_receiver_1:
                    # Assert Channel Args
                    self.assertIsInstance(outbox_row.channel_args, str)
                    self.assertEqual(frappe.parse_json(outbox_row.channel_args), sms_args_special)
                else:
                    # Global Channel Args
                    self.assertIsInstance(outbox_row.channel_args, str)
                    self.assertEqual(frappe.parse_json(outbox_row.channel_args), sms_args)

    def test_validate_can_fork(self):
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            key=self.faker.first_name(),
            lang="en",
            content=self.faker.last_name(),
            subject=self.faker.first_name(),
        ))

        # When the template being forked is already another fork
        d.is_fork_of = self.templates[0].name
        with self.assertRaises(InvalidTemplateForking):
            d.validate_can_fork()

        # When the template is created by some non-manager client
        d.is_fork_of = None
        d.created_by = self.clients.get_non_manager_client().name
        with self.assertRaises(InvalidTemplateForking):
            d.validate_can_fork()

        # When no active notification-client exists
        d.created_by = self.clients.get_manager_client().name
        set_active_notification_client(None)
        with self.assertRaises(NotificationClientNotFound):
            d.validate_can_fork()

        # When the creator itself is trying to fork his own template
        set_active_notification_client(d.created_by)
        with self.assertRaises(InvalidTemplateForking):
            d.validate_can_fork()

        # When the template being forked belongs to another manager, not the
        # manager of current client
        another_manager = [
            x for x in self.clients if x.is_client_manager and x.name != d.created_by][0].name
        set_active_notification_client(self.clients.get_clients_managed_by(another_manager)[0].name)
        with self.assertRaises(InvalidTemplateForking):
            d.validate_can_fork()

        # valid case
        set_active_notification_client(self.clients.get_clients_managed_by(d.created_by)[0].name)
        self.assertTrue(d.validate_can_fork())

    def test_fork(self):
        d = NotificationTemplate(dict(
            doctype="Notification Template",
            key=self.faker.first_name(),
            lang="en",
            content=self.faker.last_name(),
            subject=self.faker.first_name(),
        ))
        d.created_by = self.clients.get_manager_client().name
        d.insert()
        self.templates.add_document(d)

        _active_client = self.clients.get_clients_managed_by(d.created_by)[0].name
        set_active_notification_client(_active_client)
        self.assertTrue(d.validate_can_fork())

        fork_d = d.fork()
        self.templates.add_document(fork_d)

        self.assertIsInstance(fork_d, NotificationTemplate)
        self.assertEqual(d.key, fork_d.key)
        self.assertEqual(fork_d.is_fork_of, d.name)

        # Make sure Notification Client Entry was made
        _active_client: NotificationClient = frappe.get_doc("Notification Client", _active_client)
        self.assertGreater(len(_active_client.get(
            "custom_templates", dict(key=d.key, template=fork_d.name))), 0)

        # tearDown start
        _active_client.custom_templates = []
