import unittest

import frappe

from frappe_notification import (
    NotificationTemplate,
    NotificationOutbox,
    NotificationChannelFixtures,
    NotificationClientFixtures,
    NotificationTemplateFixtures,
    NotificationOutboxFixtures,
    NotificationTemplateNotFound,
    set_active_notification_client,
)

from ..send import send_notification, get_target_template


class TestSendNotification(unittest.TestCase):
    channels = NotificationChannelFixtures()
    clients = NotificationClientFixtures()
    templates = NotificationTemplateFixtures()
    outboxes = NotificationOutboxFixtures()

    @classmethod
    def setUpClass(cls):
        cls.channels.setUp()
        cls.clients.setUp()
        cls.templates.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.templates.tearDown()
        cls.clients.tearDown()
        cls.channels.tearDown()

    def setUp(self):
        self.outboxes.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        set_active_notification_client(None)

        self.outboxes.tearDown()

    def test_simple(self):
        """
        A manager triggering a Notification
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        template = _get_template_created_by(self.templates, manager)

        sms_channel = self.channels.get_channel("sms")
        recipients = [
            dict(channel=sms_channel, channel_id="+966 560440266", user_identifier="id-1"),
            dict(channel=sms_channel, channel_id="+966 560440267", user_identifier="id-2"),
        ]

        outbox = send_notification(
            template_key=template.key,
            context=dict(otp=2233, name=frappe.mock("first_name")),  # unrelated ctx
            recipients=recipients,
        )
        self.assertIsInstance(outbox, NotificationOutbox)
        self.outboxes.add_document(outbox)

        self.assertEqual(len(outbox.recipients), len(recipients))
        self.assertCountEqual(
            [
                (x.get("channel"), x.get("channel_id"), x.get("user_identifier"))
                for x in recipients
            ],
            [
                (x.get("channel"), x.get("channel_id"), x.get("user_identifier"))
                for x in outbox.recipients
            ],
        )

        self.assertEqual(outbox.notification_client, manager)


class TestGetTargetTemplate(unittest.TestCase):
    clients = NotificationClientFixtures()
    templates = NotificationTemplateFixtures()

    @classmethod
    def setUpClass(cls):
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()

    def setUp(self):
        self.templates.setUp()

        frappe.set_user("Guest")
        set_active_notification_client(None)

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        set_active_notification_client(None)

        self.templates.tearDown()

    def test_manager_asking_for_his_own_template(self):
        """
        A manager asking for his own template. He should get it
        """
        manager = self.clients.get_manager_client().name
        set_active_notification_client(manager)

        template = _get_template_created_by(self.templates, manager)

        t = get_target_template(key=template.key)
        self.assertEqual(t, template.name)

    def test_manager_asking_for_some_other_managers_template(self):
        """
        A manager should not be able to access a template created by another manager
        """
        manager_1 = self.clients.get_manager_client().name
        manager_2 = None
        while manager_2 is None or manager_1 == manager_2:
            manager_2 = self.clients.get_manager_client().name

        manager_2_template = _get_template_created_by(self.templates, manager_2, create_new=True)

        set_active_notification_client(manager_1)
        with self.assertRaises(NotificationTemplateNotFound):
            get_target_template(key=manager_2_template.key)

    def test_subordinate_asking_for_his_own_template(self):
        """
        A non-manager who has his created a template for himself should be able to get it
        """
        client = self.clients.get_non_manager_client().name
        set_active_notification_client(client)

        template = _get_template_created_by(self.templates, client)
        t = get_target_template(key=template.key)

        self.assertEqual(template.name, t)

    def test_subordinate_asking_for_a_fork_of_managers_template(self):
        """
        - A subordinate should get his fork template instead of the one defined by his manager
        """
        manager_1 = self.clients.get_manager_client().name
        template = _get_template_created_by(self.templates, manager_1)

        client = self.clients.get_clients_managed_by(manager_1)[0].name
        set_active_notification_client(client)

        forked_template = template.fork()
        self.templates.add_document(forked_template)

        t = get_target_template(key=template.key)
        self.assertEqual(forked_template.name, t)
        self.assertNotEqual(template.name, t)

    def test_subordinate_asking_for_another_managers_template(self):
        """
        A subordinate should not be able to access another manager's template
        """
        manager_1 = self.clients.get_manager_client().name
        manager_2 = None
        while manager_2 is None or manager_1 == manager_2:
            manager_2 = self.clients.get_manager_client().name

        manager_2_template = _get_template_created_by(self.templates, manager_2, create_new=True)

        client = self.clients.get_clients_managed_by(manager_1)[0].name
        set_active_notification_client(client)

        with self.assertRaises(NotificationTemplateNotFound):
            get_target_template(key=manager_2_template.key)


def _get_template_created_by(
        template_fixtures: NotificationTemplateFixtures,
        client: str,
        create_new=False) -> NotificationTemplate:
    """
    Pass in a Client Name and get back a Template
    We handle the rest for you
    """
    templates = template_fixtures.get_templates_created_by(client)
    if not create_new and len(templates):
        return templates[0]

    # Hm, we have to create new!
    d = frappe.get_doc(dict(
        doctype="Notification Template",
        created_by=client,
        key=f"RANDOM_TEMPLATE_{frappe.mock('random_int')}",
        subject=frappe.mock("first_name"),
        content=frappe.mock("last_name")
    ))
    d.insert(ignore_permissions=True)
    template_fixtures.add_document(d)

    return d
