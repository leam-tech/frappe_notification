import frappe
from .utils import validate_template_access


def delete_template(template: str):
    """
    Deletes the specified template
    """
    validate_template_access(template=template, ptype="delete")

    frappe.delete_doc("Notification Template", template, ignore_permissions=1)

    return True
