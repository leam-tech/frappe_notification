# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class NotificationOutboxRecipientItem(Document):
    channel: str
    channel_id: str
    user_identifier: str
    status: str
    time_sent: str
    sender_type: str
    sender: str
    seen: int
