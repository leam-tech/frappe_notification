# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from frappe_notification.utils import FrappeNotificationException


class InvalidManagerClient(FrappeNotificationException):
    def __init__(self, message: str = None, manager: str = None):
        self.error_code = "INVALID_CLIENT_MANAGER"
        self.http_status_code = 400
        self.message = message or frappe._("Invalid Client Manager")
        self.data = frappe._dict(
            manager=manager
        )


class CannotDemoteManager(FrappeNotificationException):
    def __init__(self, message: str = None, manager: str = None, dependent_clients=None):
        self.error_code = "CANNOT_DEMOTE_MANAGER"
        self.http_status_code = 400
        self.message = message or frappe._("Dependent Clients Exists")
        self.data = frappe._dict(
            manager=manager,
            dependent_clients=dependent_clients
        )


class NotificationClient(Document):
    LEN_API_KEY = 10
    LEN_API_SECRET = 15

    def autoname(self):
        title = self.title
        if self.managed_by:
            title = f"{self.title}-{self.managed_by}"

        self.name = frappe.scrub(title).replace("_", "-")

    def after_insert(self):
        self.api_key = frappe.generate_hash(length=self.LEN_API_KEY)
        self.api_secret = frappe.generate_hash(length=self.LEN_API_SECRET)

    def validate(self):
        if self.is_client_manager:
            self.managed_by = None
        else:
            self.validate_demotion()
            self.validate_manager()

    def validate_manager(self):
        if not self.managed_by:
            return

        manager = frappe.get_doc("Notification Client", self.managed_by)
        if not manager.is_client_manager:
            raise InvalidManagerClient(manager=manager.name)

    def validate_demotion(self):
        """
        Make sure that if ever this Client gets demoted from being a Manager,
        No other dependent Clients exists
        """
        if self.is_client_manager or not self.has_value_changed("is_client_manager"):
            return

        dependent_clients = frappe.get_all(
            "Notification Client", fields=[
                "name", "title"], filters={
                "managed_by": self.name})

        if not len(dependent_clients):
            return

        raise CannotDemoteManager(manager=self.name, dependent_clients=dependent_clients)

    @frappe.whitelist()
    def generate_new_secret(self):
        self.api_secret = frappe.generate_hash(length=self.LEN_API_SECRET)
        frappe.msgprint(frappe._("Secret Key Generated: {0}").format(self.api_key))
        return self.save()
