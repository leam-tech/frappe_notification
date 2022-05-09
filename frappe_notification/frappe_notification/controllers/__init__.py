from unittest import TestLoader, TestSuite


def load_tests(loader: TestLoader, test_classes, pattern):
    suite = TestSuite()
    _test_classes = []

    from .tests import get_frappe_notification_controllers_tests
    _test_classes.extend(get_frappe_notification_controllers_tests())

    for test_class in _test_classes:
        t = loader.loadTestsFromTestCase(test_class)
        suite.addTests(t)

    return suite
