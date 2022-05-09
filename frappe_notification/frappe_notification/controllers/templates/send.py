from typing import List
import frappe

from frappe_notification import (
    NotificationTemplate,
    NotificationOutbox,
    NotificationRecipientItem,
    NotificationClientNotFound,
    NotificationTemplateNotFound,
    get_active_notification_client)
from .utils import validate_template_access


def send_notification(
        template_key: str,
        context: dict,
        recipients: List[NotificationRecipientItem]) -> NotificationOutbox:
    """
    Send out a Notification
    - context.lang could be set to control the language
    """
    template = get_target_template(key=template_key)

    # Redundant, but swag :horns:
    validate_template_access(template=template, ptype="read")

    d: NotificationTemplate = frappe.get_doc("Notification Template", template)
    return d.send_notification(
        context=context,
        recipients=recipients,
    )


def get_target_template(key: str, client: str = None) -> str:
    """
    Get the template identifiable by `key`
    - key is non-unique
    - forking of templates are based off key
    """

    client = client or get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    def _get_template_created_by(_client: str):
        return next(iter(frappe.get_all("Notification Template", {
            "created_by": _client, "key": key})), frappe._dict(name=None)).name

    # Search Templates that the active template owns (includes forks)
    t = _get_template_created_by(_client=client)
    if t:
        return t

    # Search Templates that the manager of active client has defined
    manager = frappe.db.get_value("Notification Client", client, "managed_by")
    manager_template = _get_template_created_by(_client=manager)

    # Verify active client in Allowed Clients
    if manager_template and frappe.get_all("Notification Client Item", {
        "parent": manager_template,
        "parenttype": "Notification Template",
        "notification_client": client
    }):
        return manager_template

    raise NotificationTemplateNotFound(template=key)
