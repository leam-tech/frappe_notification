from frappe_notification.frappe_notification.controllers.templates import (
    get_template as _get_template,
    get_templates as _get_templates
)
from frappe_notification.utils import frappe_notification_api


@frappe_notification_api()
def get_template(template: str):
    """
    Get a single Template Doc identifiable by args-template
    """
    return _get_template(template=template)


@frappe_notification_api()
def get_templates():
    """
    Return a list of Templates
    Please note only a handful of fields on each template will be returned
    """
    return _get_templates()
