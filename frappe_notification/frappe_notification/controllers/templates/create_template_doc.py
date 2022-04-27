import frappe
from frappe_notification import (
    NotificationTemplate,
    NotificationClientNotFound,
    get_active_notification_client)


def create_template(data: dict) -> NotificationTemplate:
    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    is_manager = frappe.db.get_value("Notification Client", client, "is_client_manager")

    _fields = [
        "key",
        "subject",
        "content",
        "lang",
        "allowed_clients",
        "lang_templates",
        "channel_senders"]

    data = frappe._dict({
        k: data.get(k)
        for k in _fields
    })

    doc: NotificationTemplate = frappe.get_doc(dict(
        **data,
        doctype="Notification Template"
    ))
    doc.created_by = client

    if not is_manager:
        doc.allowed_clients = []

    doc.insert(ignore_permissions=True)

    return doc
