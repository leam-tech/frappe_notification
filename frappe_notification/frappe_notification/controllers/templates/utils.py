from typing import List, Optional

import frappe
from frappe_notification import (
    NotificationTemplateNotFound,
    NotificationClientNotFound,
    PermissionDenied,
    get_active_notification_client)


def _get_templates(client: str, conditions: Optional[List[str]] = None,
                   values: Optional[dict] = None):
    """
    An internal _get_templates function which handles template permissions
    Pass the conditions with care!
    """
    if values is None:
        values = {}
    if conditions is None:
        conditions = []
    managed_by = frappe.db.get_value("Notification Client", client, "managed_by")

    values = dict(
        **values,
        client=client,
        manager=managed_by or "no-manager",
    )

    conditions = "{} AND".format(" AND ".join(conditions)) if len(conditions) else ""

    r = frappe.db.sql(f"""
    SELECT
        template.name,
        template.created_by,
        template.key,
        template.subject
    FROM
        `tabNotification Template` template
        LEFT JOIN `tabNotification Client Item` allowed_client
            ON allowed_client.parent = template.name
            AND allowed_client.parenttype = "Notification Template"
    WHERE
        {conditions}
        (
            template.created_by = %(client)s
            OR (
                template.created_by = %(manager)s
                AND allowed_client.notification_client = %(client)s
            )
        )

    ORDER BY
        template.modified desc
    """, values, as_dict=1, debug=0)

    return r


def validate_template_access(template: str, ptype: str = "read", client: Optional[str] = None):
    """
    Verify if the template specified is either created by the client or belongs to Client's Manager
    For Updates & Deletes, only the owner can do it (only Manager if distributed)

    Raises:
        NotificationTemplateNotFound: When permission is denied or template do not exist
        NotificationClientNotFound: When active client is null
    """
    client = client or get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    if not frappe.db.exists("Notification Template", template):
        raise NotificationTemplateNotFound(template=template)

    r = _get_templates(
        client=client,
        conditions=[
            "template.name = %(template)s"
        ],
        values=dict(
            template=template
        )
    )

    if not len(r):
        raise NotificationTemplateNotFound()

    if ptype == "read":
        return
    elif ptype in ("update", "delete"):
        if r[0].created_by == client:
            pass
        else:
            raise PermissionDenied(
                message=frappe._("Only the owner can {} the Template".format(ptype)),
                doctype="Notification Template",
                name=template,
                active_client=client,
                template_owner=r[0].created_by
            )
    else:
        raise PermissionDenied(
            message=frappe._("Unknown permission type"),
            ptype=ptype
        )
