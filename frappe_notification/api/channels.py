from frappe_notification.frappe_notification.controllers.channels import (
    get_channels as _get_channels
)
from frappe_notification.utils import frappe_notification_api


@frappe_notification_api()
def get_channels():
    """
    Get a list of notification-channels with their name & titles
    """
    t = _get_channels()
    return dict(channels=t)
