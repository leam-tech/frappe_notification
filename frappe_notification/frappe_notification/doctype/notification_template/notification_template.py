# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt

from typing import List

import frappe
from frappe.model.document import Document

from frappe_notification import (
    get_active_notification_client,
    NotificationChannel,
    FrappeNotificationException,
    NotificationClientNotFound,
    NotificationChannelNotFound)
from ..notification_client_item.notification_client_item import NotificationClientItem
from ..notification_template_sender_item.notification_template_sender_item import \
    NotificationTemplateSenderItem
from ..notification_template_language_item.notification_template_language_item import \
    NotificationTemplateLanguageItem


class NotificationRecipientItem():
    channel: str
    channel_id: str


class OnlyManagerTemplatesCanBeShared(FrappeNotificationException):
    def __init__(self) -> None:
        self.error_code = "ONLY_MANAGER_TEMPLATES_CAN_BE_SHARED"
        self.http_status_code = 400
        self.message = frappe._("Only the templates created by Client Managers can be shared")


class AllowedClientNotManagedByManager(FrappeNotificationException):
    def __init__(self, template_manager: str, client: str, client_manager: str) -> None:
        self.error_code = "ALLOWED_CLIENT_NOT_MANAGED_BY_MANAGER"
        self.http_status_code = 400
        self.message = frappe._("Template can only be shared between clients"
                                " that are managed by the manager of this template")
        self.data = frappe._dict(
            template_manager=template_manager,
            client=client,
            client_manager=client_manager)


class NotificationTemplate(Document):
    title: str
    subject: str
    content: str
    lang: str
    last_used_on: str
    last_used_by: str
    created_by: str
    allowed_clients: List[NotificationClientItem]
    lang_templates: List[NotificationTemplateLanguageItem]
    channel_senders: List[NotificationTemplateSenderItem]

    def autoname(self):
        client = self.created_by or get_active_notification_client()
        # Client name already includes manager name if specified
        if not client:
            raise NotificationClientNotFound()

        self.name = frappe.scrub(f"{client}-{self.title}").replace("_", "-")

    def before_insert(self):
        client = self.created_by or get_active_notification_client()
        if client:
            self.created_by = client

    def validate(self):
        if not self.lang:
            self.lang = "en"
        self.validate_allowed_clients()
        self.validate_language_templates()

    def validate_allowed_clients(self):
        """
        Notification Templates created_by ClientManager can only be shared with subordinate-clients
        """
        if not len(self.allowed_clients):
            return

        # Verify the owner is actually a ClientManager
        is_client_manager = frappe.db.get_value(
            "Notification Client",
            self.created_by,
            "is_client_manager") if self.created_by else False

        if not is_client_manager:
            self.allowed_clients = []
            raise OnlyManagerTemplatesCanBeShared()

        # Validate all the clients specified are actually managed by the creator
        clients = frappe.get_all(
            "Notification Client",
            ["name", "managed_by", "is_client_manager"],
            {"name": ["IN", [x.notification_client for x in self.allowed_clients]]}
        )

        for client in clients:
            if client.managed_by != self.created_by:
                raise AllowedClientNotManagedByManager(
                    template_manager=self.created_by,
                    client=client.name,
                    client_manager=client.managed_by)

    def validate_language_templates(self):
        i = 0
        languages_defined = []
        if self.lang:
            languages_defined.append(self.lang)

        while i < len(self.lang_templates):
            row = self.lang_templates[i]
            remove_row = False
            if not row.subject and not row.content:
                remove_row = True

            if row.lang not in languages_defined:
                languages_defined.append(row.lang)
            else:
                remove_row = True

            if remove_row:
                self.lang_templates.remove(row)
                continue

            i += 1

    def send_notification(self, context: dict, recipients: List[NotificationRecipientItem]):
        pass

    def make_outbox_entry(self):
        pass

    def get_lang_templates(self, lang: str):
        """
        Gets the templates (subject & content) defined for a particular language
        """
        subject = self.subject
        content = self.content

        if self.lang == lang:
            return (subject, content)

        for row in self.lang_templates:
            if row.lang != lang:
                continue
            return (row.subject, row.content)

        return (subject, content)

    def get_channel_sender(self, channel: str):
        """
        Senders can be Email Account, Telegram Bot
        """
        if not frappe.db.exists("Notification Channel", channel):
            raise NotificationChannelNotFound(channel=channel)

        # Search in the template itself
        for row in self.channel_senders:
            if row.channel != channel:
                continue
            return (row.sender_type, row.sender)

        channel: NotificationChannel = frappe.get_doc("Notification Channel", channel)
        return (channel.sender_type, channel.default_sender)
