
__version__ = '0.0.1'

from .utils.exceptions import *  # noqa
from .utils.client import get_active_notification_client, set_active_notification_client  # noqa
from .frappe_notification.doctype.notification_client import NotificationClient, NotificationClientFixtures  # noqa
from .frappe_notification.doctype.notification_channel import NotificationChannel, NotificationChannelFixtures  # noqa
from .frappe_notification.doctype.notification_outbox import NotificationOutbox, NotificationOutboxStatus, NotificationOutboxFixtures, RecipientsBatchItem  # noqa
from .frappe_notification.doctype.notification_template import NotificationTemplate, NotificationRecipientItem, NotificationTemplateFixtures  # noqa


from unittest import TestLoader, TestSuite


def load_tests(loader: TestLoader, test_classes, pattern):
    suite = TestSuite()
    _test_classes = []

    from .frappe_notification.controllers.tests import get_frappe_notification_controllers_tests
    from .frappe_notification.doctype.tests import get_frappe_notification_doctype_tests

    _test_classes.extend(get_frappe_notification_doctype_tests())
    _test_classes.extend(get_frappe_notification_controllers_tests())

    for test_class in _test_classes:
        t = loader.loadTestsFromTestCase(test_class)
        suite.addTests(t)

    return suite
