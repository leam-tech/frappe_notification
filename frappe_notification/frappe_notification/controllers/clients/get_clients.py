import frappe

from frappe_notification import (
    PermissionDenied,
    get_active_notification_client
)


def get_notification_clients():
    """
    Get list of Clients that the active manager commands
    """
    client = get_active_notification_client()
    if not frappe.db.get_value("Notification Client", client, "is_client_manager"):
        raise PermissionDenied(message=frappe._("Only a Manager can list clients"))

    return frappe.db.get_all(
        "Notification Client",
        ["name", "title", "url", ],
        {"managed_by": client},
        limit_page_length=999,
    )
