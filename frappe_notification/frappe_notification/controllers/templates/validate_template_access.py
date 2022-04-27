from typing import Optional

import frappe
from frappe_notification import (
    NotificationTemplateNotFound,
    NotificationClientNotFound,
    get_active_notification_client)


def validate_template_access(template: str, client: Optional[str] = None):
    """
    Verify if the template specified is either created by the client or belongs to Client's Manager

    Raises:
        NotificationTemplateNotFound: When permission is denied or template do not exist
        NotificationClientNotFound: When active client is null
    """
    client = client or get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    if not frappe.db.exists("Notification Template", template):
        raise NotificationTemplateNotFound(template=template)

    managed_by = frappe.db.get_value("Notification Client", client, "managed_by")

    r = frappe.db.sql("""
    SELECT
        template.name
    FROM `tabNotification Template` template
    LEFT JOIN `tabNotification Client Item` allowed_client
        ON allowed_client.parent = template.name
            AND allowed_client.parenttype = "Notification Template"
    WHERE
        template.name = %(template)s
        AND (
            template.created_by = %(client)s OR
            (template.created_by = %(manager)s AND allowed_client.notification_client = %(client)s)
        )
    """, dict(
        template=template,
        client=client,
        manager=managed_by,
    ), debug=0)

    if not len(r):
        raise NotificationTemplateNotFound()
