import frappe

from frappe_notification import (NotificationTemplate)

from .utils import validate_template_access


def get_template(template: str) -> NotificationTemplate:
    """
    - Validate if the current client has access to the template
    - Return NotificationTemplate
    """

    validate_template_access(template=template)

    return frappe.get_doc("Notification Template", template)
