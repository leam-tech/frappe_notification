import frappe
from frappe_notification import (
    NotificationClient,
)
from .utils import validate_client_access


def update_notification_client(client: str, data: dict) -> NotificationClient:
    """
    Updates a Notification Client
    """
    validate_client_access(client=client)

    _fields = ["title", "url"]
    data = frappe._dict({
        k: data.get(k)
        for k in _fields
    })

    d = frappe.get_doc("Notification Client", client)
    d.update(data)
    d.save(ignore_permissions=True)

    return d
