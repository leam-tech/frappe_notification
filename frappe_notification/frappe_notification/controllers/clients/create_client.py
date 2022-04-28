import frappe
from frappe_notification import (
    NotificationClient,
    PermissionDenied,
    get_active_notification_client)


def create_notification_client(data: dict):
    """
    Creates a Notification Client and returns it along with its API Secret
    """
    client = get_active_notification_client()
    if not frappe.db.get_value("Notification Client", client, "is_client_manager"):
        raise PermissionDenied(message=frappe._("Only a Manager can create clients"))

    _fields = ["title", "url"]
    data = frappe._dict({
        k: data.get(k)
        for k in _fields
    })

    d = NotificationClient(dict(
        **data,
        doctype="Notification Client",
        managed_by=client,
        enabled=1,
    ))

    d.insert(ignore_permissions=True)

    # Unmask API Secret before return
    d.api_secret = d.get_password("api_secret")
    return d
