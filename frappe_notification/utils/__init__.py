from functools import wraps


import frappe
from .client import get_active_notification_client, set_active_notification_client  # noqa
from .exceptions import *  # noqa


def frappe_notification_api(only_client_managers=False, allow_non_clients=False):
    """
    Wrapper for frappe_notification API

    args:
        only_client_managers (bool): Allow this endpoint only for managers
    """
    from .exceptions import (
        FrappeNotificationException,
        NotificationClientNotFound,
        ActionRestrictedToClientManager)

    def _inner_0(fn):

        @wraps(fn)
        def _inner_1(*args, **kwargs):
            try:
                client: str = get_active_notification_client()
                if not allow_non_clients and not client:
                    raise NotificationClientNotFound()
                if only_client_managers and not frappe.db.get_value(
                        "Notification Client", client, "is_client_manager"):
                    raise ActionRestrictedToClientManager()

                return fn(*args, **kwargs)
            except FrappeNotificationException as e:
                frappe.local.response['http_status_code'] = e.http_status_code
                return e.as_dict()
            except BaseException as e:
                frappe.local.response['http_status_code'] = 500
                return frappe._dict(
                    error_code="UNKNOWN_SERVER_ERROR",
                    message=frappe._("Unknown Server Error occurred: {0}").format(str(e)),
                    traceback=frappe.get_traceback()
                )

        frappe.whitelist(allow_guest=True)(_inner_1)
        return _inner_1

    return _inner_0
