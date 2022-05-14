from typing import Optional

import frappe
from frappe_notification import (
    NotificationClientNotFound,
    get_active_notification_client)


def get_notification_logs(
        channel: str,
        channel_id: str,
        limit_start: Optional[int] = 0,
        limit_page_length: Optional[int] = 10,
        order_by: Optional[str] = "creation desc"):
    """
    Fetches a list of Notifications sent to a specific user via specific channel
    """

    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    joins = []
    conditions = []
    if channel:
        joins.append("""

        """)
        conditions.append("""
            recipient_item.channel = %(channel)s
        """)

    return frappe.db.sql("""
    SELECT
        outbox.name as outbox,
        recipient_item.name as outbox_recipient_row,
        outbox.subject,
        outbox.content,
        recipient_item.time_sent
    FROM
        `tabNotification Outbox` outbox
    JOIN `tabNotification Outbox Recipient Item` recipient_item
        ON recipient_item.parent = outbox.name AND recipient_item.parenttype = "Notification Outbox"
    WHERE
        outbox.notification_client = %(client)s
        AND outbox.docstatus = 1
        AND recipient_item.channel = %(channel)s
        AND recipient_item.channel_id = %(channel_id)s
        AND recipient_item.status = "Success"
    ORDER BY %(order_by)s
    LIMIT %(limit_start)s, %(limit_page_length)s
    """, {
        "client": client,
        "channel": channel,
        "channel_id": channel_id,
        "limit_start": limit_start,
        "limit_page_length": limit_page_length,
        "order_by": order_by
    }, as_dict=1)
