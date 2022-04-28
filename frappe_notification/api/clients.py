
from frappe_notification.frappe_notification.controllers.clients import (
    create_notification_client as _create_notification_client,
    update_notification_client as _update_notification_client
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
