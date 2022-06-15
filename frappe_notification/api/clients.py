from typing import Optional

from frappe_notification.frappe_notification.controllers.clients import (
    create_notification_client as _create_notification_client,
    update_notification_client as _update_notification_client,
    get_notification_clients as _get_notification_clients,
    get_notification_client as _get_notification_client,
    get_notification_logs as _get_notification_logs,
    mark_log_seen as _mark_log_seen,
    get_me as _get_me
)
from frappe_notification.frappe_notification.controllers.clients.get_notification_logs import \
    GetNotificationLogsExecutionArgs
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


@frappe_notification_api()
def get_notification_logs(args:GetNotificationLogsExecutionArgs):
    """
    Fetches a list of Notifications sent to a specific user via specific channel
    """
    return _get_notification_logs(args)


@frappe_notification_api()
def mark_log_seen(
        outbox: str,
        channel: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_identifier: Optional[str] = None,
        outbox_recipient_row: Optional[str] = None,
):
    """
    Marks a particular log as seen. Information on how to treat the parameters can be
    found in the controller method
    """
    t = _mark_log_seen(
        outbox=outbox,
        channel=channel,
        channel_id=channel_id,
        user_identifier=user_identifier,
        outbox_recipient_row=outbox_recipient_row,
    )

    return dict(marked=t)
