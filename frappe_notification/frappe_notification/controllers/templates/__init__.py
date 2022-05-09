from .get_template_doc import get_template  # noqa
from .get_templates_list import get_templates  # noqa
from .update_template_doc import update_template  # noqa
from .delete_template_doc import delete_template  # noqa
from .create_template_doc import create_template  # noqa
from .fork_template_doc import fork_template  # noqa
from .send import send_notification  # noqa


from unittest import TestLoader, TestSuite


def load_tests(loader: TestLoader, test_classes, pattern):
    suite = TestSuite()
    _test_classes = []

    from .tests import get_template_controller_tests
    _test_classes.extend(get_template_controller_tests())

    for test_class in _test_classes:
        t = loader.loadTestsFromTestCase(test_class)
        suite.addTests(t)

    return suite
