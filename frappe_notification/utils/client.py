import frappe
from typing import Union


AUTH_HEADER = "X-Notifications-Token"


def get_active_notification_client() -> Union[str, None]:
    import base64

    if getattr(frappe.local, "notification_client", None):
        return frappe.local.notification_client

    header = frappe.safe_decode(frappe.get_request_header(AUTH_HEADER, str())) \
        if frappe.request else None
    if not header:
        return None

    try:
        header = header.split(" ")
        if header[0].lower() == "basic":
            api_key, api_secret = frappe.safe_decode(
                base64.b64decode(header[1])).split(":")
        elif header[0].lower() == "token":
            api_key, api_secret = header[1].split(":")
        else:
            raise Exception("Invalid Token")
    except BaseException:
        return None

    doctype = "Notification Client"
    client = frappe.db.get_value(doctype, {"api_key": api_key})
    if not client:
        return None

    doc_secret = frappe.utils.password.get_decrypted_password(
        doctype, client, fieldname='api_secret')

    if doc_secret != api_secret:
        return None

    set_active_notification_client(client)
    return client


def set_active_notification_client(client: str):
    frappe.local.notification_client = client
