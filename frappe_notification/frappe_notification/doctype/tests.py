from .notification_channel.test_notification_channel import TestNotificationChannel
from .notification_client.test_notification_client import TestNotificationClient
from .notification_outbox.test_notification_outbox import TestNotificationOutbox
from .notification_template.test_notification_template import TestNotificationTemplate


def get_frappe_notification_doctype_tests():
    return [
        TestNotificationChannel,
        TestNotificationClient,
        TestNotificationOutbox,
        TestNotificationTemplate,
    ]
