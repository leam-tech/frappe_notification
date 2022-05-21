from .create_client import create_notification_client  # noqa
from .update_client import update_notification_client  # noqa
from .get_clients import get_notification_clients  # noqa
from .get_client import get_notification_client  # noqa
from .get_me import get_me  # noqa
from .get_notification_logs import get_notification_logs  # noqa
from .mark_log_seen import mark_log_seen  # noqa


from unittest import TestLoader, TestSuite


def load_tests(loader: TestLoader, test_classes, pattern):
    suite = TestSuite()
    _test_classes = []

    from .tests import get_clients_controller_tests
    _test_classes.extend(get_clients_controller_tests())

    for test_class in _test_classes:
        t = loader.loadTestsFromTestCase(test_class)
        suite.addTests(t)

    return suite
