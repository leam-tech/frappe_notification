from typing import Optional

import frappe
from frappe_notification import (
    NotificationClientNotFound,
    NotificationOutbox,
    NotificationOutboxNotFound,
    get_active_notification_client)


def mark_log_seen(
        outbox: str,
        channel: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_identifier: Optional[str] = None,
        outbox_recipient_row: Optional[str] = None,
):
    """
    Marks a specific recipient of the outbox as seen.
    You can ask to be marked as seen in 3 ways:
    - Specify channel & channel_id
    - Specify the name of the outbox_recipient_row name
    - Specify the user_identifier
    """

    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    if not frappe.db.exists("Notification Outbox", {"name": outbox, "notification_client": client}):
        raise NotificationOutboxNotFound(outbox=outbox)

    outbox: NotificationOutbox = frappe.get_doc("Notification Outbox", outbox)

    _row = None
    if channel and channel_id:
        _row = [x for x in outbox.recipients if x.channel == channel and x.channel_id == channel_id]

    if user_identifier:
        _row = [x for x in outbox.recipients if x.user_identifier == user_identifier]

    if outbox_recipient_row:
        _row = [x for x in outbox.recipients if x.name == outbox_recipient_row]

    if _row and isinstance(_row, list):
        _row = _row[0]

    if not _row:
        raise NotificationOutboxNotFound(outbox=outbox.name)

    _row.db_set("seen", 1)

    return True
