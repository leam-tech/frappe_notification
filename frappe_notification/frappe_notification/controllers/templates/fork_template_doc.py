import frappe
from frappe_notification import (
    NotificationTemplate,
)
from .utils import validate_template_access


def fork_template(template: str):
    """
    Fork a template
    You will need read access on the template being forked
    """
    validate_template_access(template=template, ptype="read")

    d: NotificationTemplate = frappe.get_doc("Notification Template", template)
    fork = d.fork()

    return fork
