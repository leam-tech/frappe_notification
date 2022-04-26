from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_notification import (
    NotificationClientFixtures,
    NotificationClientNotFound,
    ActionRestrictedToClientManager)
from frappe_notification.utils import frappe_notification_api, set_active_notification_client


def test_api_handler(*args, **kwargs):
    pass


class TestFrappeNotificationAPI(TestCase):
    """
    Expose apis without need for any login (Guests)
    """

    clients = NotificationClientFixtures()

    @classmethod
    def setUpClass(cls):
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.clients.tearDown()

    def setUp(self):
        frappe.set_user("Guest")

    def tearDown(self) -> None:
        set_active_notification_client(None)
        frappe.set_user("Administrator")

    @patch(f"{__module__}.test_api_handler")
    def test_allow_non_clients(self, _test_api_handler: MagicMock):
        """
        - If allow_non_clients is True, allow anybody to invoke
        """
        wrapped = frappe_notification_api(allow_non_clients=True)(test_api_handler)

        wrapped(a=1, b=2)

        _test_api_handler.assert_called_once_with(a=1, b=2)
        frappe.is_whitelisted(test_api_handler)

    @patch(f"{__module__}.test_api_handler")
    def test_only_for_clients(self, _test_api_handler: MagicMock):
        """
        When allow_non_clients is False, make sure errors are raised when not logged in
        """
        wrapped = frappe_notification_api(allow_non_clients=False)(test_api_handler)
        r = wrapped(a=1, b=2)
        _test_api_handler.assert_not_called()

        exc = NotificationClientNotFound()

        self.assertIsInstance(r, dict)
        self.assertEqual(r.get("error_code"), exc.error_code)

        # Now, lets set an active client
        set_active_notification_client(self.clients.get_non_manager_client().name)
        r = wrapped(a=1, b=1)
        _test_api_handler.assert_called_once_with(a=1, b=1)

    @patch(f"{__module__}.test_api_handler")
    def test_only_client_managers(self, _test_api_handler: MagicMock):
        """
        Test only_client_managers
        """

        set_active_notification_client(self.clients.get_non_manager_client().name)

        wrapped = frappe_notification_api(only_client_managers=True)(test_api_handler)
        r = wrapped(a=1, b=2)
        _test_api_handler.assert_not_called()

        exc = ActionRestrictedToClientManager()
        self.assertIsInstance(r, dict)
        self.assertEqual(r.get("error_code"), exc.error_code)

        # Now, lets set an active manager
        set_active_notification_client(self.clients.get_manager_client().name)
        r = wrapped(a=1, b=1)
        _test_api_handler.assert_called_once_with(a=1, b=1)
