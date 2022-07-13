from unittest import TestCase

from frappe_notification import (
    NotificationClientFixtures,
    PermissionDenied,
    set_active_notification_client)

from ..utils import validate_client_access


class TestValidateClientAccess(TestCase):
    clients: NotificationClientFixtures = None

    @classmethod
    def setUpClass(cls):
        cls.clients = NotificationClientFixtures()
        cls.clients.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.clients.tearDown()

    def test_non_manager_client(self):
        """
        A non-manager client asking for some other non-manager client
        """
        client = self.clients.get_non_manager_client()
        set_active_notification_client(client.name)

        with self.assertRaises(PermissionDenied):
            validate_client_access(
                client=self.clients.get_non_manager_client().name
            )

    def test_non_manager_client_asking_for_himself(self):
        """
        A non manager client wanting to access himself
        """
        client = self.clients.get_non_manager_client()
        set_active_notification_client(client.name)

        with self.assertRaises(PermissionDenied):
            validate_client_access(
                client=client.name
            )

    def test_a_manager_asking_for_himself(self):
        """
        A manager asking for himself
        """

        manager = self.clients.get_manager_client()
        set_active_notification_client(manager.name)

        with self.assertRaises(PermissionDenied):
            validate_client_access(manager.name)

    def test_a_manager_asking_for_another_manager(self):
        """
        A manager asking for another manager
        """
        manager_1 = self.clients.get_manager_client().name
        manager_2 = None
        while manager_2 is None or manager_2 == manager_1:
            manager_2 = self.clients.get_manager_client().name

        set_active_notification_client(manager_1)

        with self.assertRaises(PermissionDenied):
            validate_client_access(manager_2)

    def test_a_manager_asking_for_subordinate(self):
        """
        A manager asking for his subordintate -- Valid
        """
        manager_1 = self.clients.get_manager_client().name
        client_1 = self.clients.get_clients_managed_by(manager_1)[0].name

        set_active_notification_client(manager_1)

        validate_client_access(client_1)
