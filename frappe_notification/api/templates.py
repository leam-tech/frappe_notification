from typing import List
from frappe_notification.frappe_notification.controllers.templates import (
    get_template as _get_template,
    get_templates as _get_templates,
    update_template as _update_template,
    delete_template as _delete_template,
    create_template as _create_template,
    fork_template as _fork_template,
    send_notification as _send_notification
)
from frappe_notification.utils import frappe_notification_api


@frappe_notification_api()
def send_notification(
        template_key: str,
        context: dict,
        recipients: List[dict]):
    """
    Send out the notification to recipients
    """
    t = _send_notification(
        context=context,
        template_key=template_key,
        recipients=recipients
    )
    return t.as_dict()


@frappe_notification_api()
def get_template(template: str):
    """
    Get a single Template Doc identifiable by args-template
    """
    t = _get_template(template=template)
    return t.as_dict()


@frappe_notification_api()
def get_templates():
    """
    Return a list of Templates
    Please note only a handful of fields on each template will be returned
    """
    return dict(templates=_get_templates())


@frappe_notification_api()
def update_template(template: str, data: dict):
    """
    Update a template's contents
    Please note that only a subset of fields can be edited
    """
    t = _update_template(template=template, data=data)
    return t.as_dict()


@frappe_notification_api()
def delete_template(template: str):
    """
    Delete a specific template
    """
    return _delete_template(template=template)


@frappe_notification_api()
def create_template(data: dict):
    """
    Creates a template under the active client
    """
    t = _create_template(data)
    return t.as_dict()


@frappe_notification_api()
def fork_template(template: str):
    """
    Fork a specific template to make a copy
    """
    t = _fork_template(template=template)
    return t.as_dict()
