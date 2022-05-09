import frappe
from frappe_notification import ValidationError
from .utils import validate_template_access


def update_template(template: str, updates: dict):
    """
    - Updates are allowed only to the creator of the template
    - Only a handful of fields defined below can be updated
    """

    validate_template_access(template=template, ptype="update")

    _fields = ["subject", "content", "lang", "allowed_clients", "lang_templates", "channel_senders"]
    updates = frappe._dict({
        k: updates.get(k)
        for k in _fields
    })

    d = frappe.get_doc("Notification Template", template)
    d.update(updates)
    try:
        d.save(ignore_permissions=True)
    except frappe.exceptions.ValidationError as e:
        raise ValidationError(str(e))

    return d
