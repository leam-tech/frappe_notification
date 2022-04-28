import frappe
from frappe_notification import (
    NotificationClient,
)
from .utils import validate_client_access


def update_notification_client(client: str, updates: dict) -> NotificationClient:
    """
    Updates a Notification Client
    """
    validate_client_access(client=client)

    _fields = ["title", "url"]
    updates = frappe._dict({
        k: updates.get(k)
        for k in _fields
    })

    d = frappe.get_doc("Notification Client", client)
    d.update(updates)
    d.save(ignore_permissions=True)

    return d
