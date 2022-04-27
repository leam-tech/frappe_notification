from frappe_notification.frappe_notification.controllers.templates import (
    get_template as _get_template,
    get_templates as _get_templates,
    update_template as _update_template,
    delete_template as _delete_template,
    create_template as _create_template,
    fork_template as _fork_template,
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


@frappe_notification_api()
def update_template(template: str, updates: dict):
    """
    Update a template's contents
    Please note that only a subset of fields can be edited
    """
    return _update_template(template=template, updates=updates)


@frappe_notification_api()
def delete_template(template: str):
    """
    Delete a specific template
    """
    return _delete_template(template=template)


@frappe_notification_api
def create_template(data: dict):
    """
    Creates a template under the active client
    """
    return _create_template(data)


@frappe_notification_api
def fork_template(template: str):
    """
    Fork a specific template to make a copy
    """
    return _fork_template(template=template)
