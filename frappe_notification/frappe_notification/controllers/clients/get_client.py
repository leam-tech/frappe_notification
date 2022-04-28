import frappe

from frappe_notification import NotificationClient
from .utils import validate_client_access


def get_notification_client(client: str) -> NotificationClient:
    """
    Get a single Notification Client
    """
    validate_client_access(client=client)

    return frappe.get_doc("Notification Client", client)
