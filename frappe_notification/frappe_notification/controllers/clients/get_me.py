import frappe
from frappe_notification import (
    NotificationClient,
    NotificationClientNotFound,
    get_active_notification_client)


def get_me():
    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    client: NotificationClient = frappe.get_doc("Notification Client", client)
    return frappe._dict(
        notification_client=client.name,
        title=client.title,
        url=client.url,
        enabled=client.enabled,
        is_client_manager=client.is_client_manager,
        managed_by=client.managed_by,
    )
