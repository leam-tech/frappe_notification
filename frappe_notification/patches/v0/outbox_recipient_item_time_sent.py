import frappe
from frappe.utils import now_datetime
from frappe_notification.frappe_notification.doctype.notification_outbox.notification_outbox \
    import NotificationOutboxStatus


def execute():
    recipient_items = frappe.get_all(
        "Notification Outbox Recipient Item",
        fields=["name", "creation"],
        filters=dict(
            status=NotificationOutboxStatus.SUCCESS.value,
            time_sent=["is", "not set"]
        ))

    for item in recipient_items:
        frappe.db.set_value(
            "Notification Outbox Recipient Item",
            item.name,
            "time_sent",
            item.creation or now_datetime()
        )
