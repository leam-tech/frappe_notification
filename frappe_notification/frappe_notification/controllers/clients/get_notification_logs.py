from typing import Optional

import frappe
from frappe_notification import (
    NotificationClientNotFound,
    InvalidRequest,
    get_active_notification_client)


def get_notification_logs(
        channel: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_identifier: Optional[str] = None,
        limit_start: Optional[int] = 0,
        limit_page_length: Optional[int] = 10,
        order_by: Optional[str] = "creation desc"):
    """
    Fetches a list of Notifications sent to a specific user via specific channel
    """

    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    if not ((channel and channel_id) or user_identifier):
        raise InvalidRequest(message=frappe._(
            "Please specify either (channel, channel_id) or user_identifier"
        ))

    conditions = []
    if channel:
        conditions.append("recipient_item.channel = %(channel)s")

    if channel_id:
        conditions.append("recipient_item.channel_id = %(channel_id)s")

    if user_identifier:
        conditions.append("recipient_item.user_identifier = %(user_identifier)s")

    conditions = " AND {}".format(" AND ".join(conditions)) if len(conditions) else ""

    return frappe.db.sql(f"""
    SELECT
        outbox.name as outbox,
        recipient_item.name as outbox_recipient_row,
        outbox.subject,
        outbox.content,
        recipient_item.time_sent,
        recipient_item.user_identifier,
        recipient_item.channel,
        recipient_item.channel_id,
        recipient_item.seen
    FROM
        `tabNotification Outbox` outbox
    JOIN `tabNotification Outbox Recipient Item` recipient_item
        ON recipient_item.parent = outbox.name AND recipient_item.parenttype = "Notification Outbox"
    WHERE
        outbox.notification_client = %(client)s
        AND outbox.docstatus = 1
        {conditions}
        AND recipient_item.status = "Success"
    ORDER BY %(order_by)s
    LIMIT %(limit_start)s, %(limit_page_length)s
    """, {
        "client": client,
        "channel": channel,
        "channel_id": channel_id,
        "user_identifier": user_identifier,
        "limit_start": limit_start,
        "limit_page_length": limit_page_length,
        "order_by": order_by
    }, as_dict=1, debug=0)
