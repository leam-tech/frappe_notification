from typing import List

import frappe
from frappe_notification import (NotificationClientNotFound, get_active_notification_client)


def get_channels() -> List[dict]:
    """
    Returns a list of channels accessible for the active notification client
    Right now, all the channels are accessible for all clients.
    Later, we might have restricted channel accessibility
    """
    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    return frappe.get_all(
        "Notification Channel",
        fields=["name", "title"],
        filters={"enabled": 1},
    )
