
from frappe_notification.frappe_notification.controllers.clients import (
    create_notification_client as _create_notification_client,
    update_notification_client as _update_notification_client,
    get_notification_clients as _get_notification_clients
)
from frappe_notification.utils import frappe_notification_api


@frappe_notification_api(only_client_managers=True)
def create_notification_client(data: dict):
    """
    Create a Notification Client under a Manager
    """
    return _create_notification_client(data=data)


@frappe_notification_api(only_client_managers=True)
def update_notification_client(client: str, updates: dict):
    """
    Update a Notification Client under a Manager
    """
    return _update_notification_client(client=client, updates=updates)


@frappe_notification_api(only_client_managers=True)
def get_notification_clients():
    """
    Get a list of clients managed by active manager
    """
    return _get_notification_clients()
