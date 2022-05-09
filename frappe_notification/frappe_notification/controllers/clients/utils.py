import frappe
from frappe_notification import (
    NotificationClientNotFound,
    PermissionDenied,
    get_active_notification_client)


def validate_client_access(client: str, manager: str = None):
    """
    Validation for client.managed_by field
    """
    manager = manager or get_active_notification_client()
    if not manager:
        raise NotificationClientNotFound()

    is_client_manager = frappe.db.get_value("Notification Client", manager, "is_client_manager")
    if not is_client_manager:
        raise PermissionDenied(
            message=frappe._("You are not a Client Manager"),
            notification_client=client,
        )

    managed_by = frappe.db.get_value("Notification Client", client, "managed_by")
    if managed_by != manager:
        raise PermissionDenied(
            message=frappe._("You do not manage this client"),
            notification_client=client,
        )
