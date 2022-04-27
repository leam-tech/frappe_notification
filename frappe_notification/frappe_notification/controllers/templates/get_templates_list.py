
from frappe_notification import (
    NotificationClientNotFound,
    get_active_notification_client)

from .utils import _get_templates


def get_templates():
    """
    Gets a list of Templates that the active client can access
    """
    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    r = _get_templates(client=client)

    return r
