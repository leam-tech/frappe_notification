
from frappe_notification.frappe_notification.controllers.clients import (
    create_notification_client as _create_notification_client,
    update_notification_client as _update_notification_client,
    get_notification_clients as _get_notification_clients,
    get_notification_client as _get_notification_client,
    get_me as _get_me
)
from frappe_notification.utils import frappe_notification_api


@frappe_notification_api(only_client_managers=True)
def create_notification_client(data: dict):
    """
    Create a Notification Client under a Manager
    """
    client = _create_notification_client(data=data)
    return client.as_dict()


@frappe_notification_api(only_client_managers=True)
def update_notification_client(client: str, data: dict):
    """
    Update a Notification Client under a Manager
    """
    client = _update_notification_client(client=client, data=data)
    return client.as_dict()


@frappe_notification_api(only_client_managers=True)
def get_notification_clients():
    """
    Get a list of clients managed by active manager
    """
    return dict(clients=_get_notification_clients())


@frappe_notification_api(only_client_managers=True)
def get_notification_client(client: str):
    """
    Get a single client that is managed by active manager
    """
    client = _get_notification_client(client=client)
    return client.as_dict()


@frappe_notification_api(only_client_managers=False)
def get_me():
    """
    Get active client info
    """
    return _get_me()
