# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class NotificationChannel(Document):
    title: str
    sender_type: str
    default_sender: str
