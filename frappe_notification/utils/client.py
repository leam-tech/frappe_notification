import frappe


def get_active_notification_client():
    import base64

    if hasattr(frappe.local, "notification_client"):
        return frappe.local.notification_client

    header = frappe.safe_decode(frappe.get_request_header("Authorization", str()))
    if not header:
        return None

    header = header.split(" ")
    if header[0].lower() == "basic":
        api_key, api_secret = frappe.safe_decode(
            base64.b64decode(frappe.safe_encode(header[1]))).split(":")
    elif header[0].lower() == "token":
        api_key, api_secret = header[1].split(":")

    doctype = "Notification Client"
    client = frappe.db.get_value(doctype=doctype, filters={"api_key": api_key},)

    doc_secret = frappe.utils.password.get_decrypted_password(
        doctype, client, fieldname='api_secret')

    if doc_secret != api_secret:
        return None

    frappe.local.notification_client = client
    return client
