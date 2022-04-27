# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt

from typing import List

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from frappe_notification import (
    get_active_notification_client,
    NotificationChannel,
    NotificationOutbox,
    FrappeNotificationException,
    NotificationClientNotFound,
    NotificationChannelNotFound)

from ..notification_client_item.notification_client_item import NotificationClientItem
from ..notification_template_sender_item.notification_template_sender_item import \
    NotificationTemplateSenderItem
from ..notification_template_language_item.notification_template_language_item import \
    NotificationTemplateLanguageItem


class NotificationRecipientItem(frappe._dict):
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


class InvalidTemplateForking(FrappeNotificationException):
    def __init__(self, template: str, error_code: str = None, message: str = None):
        self.error_code = error_code or "INVALID_TEMPLATE_FORKING"
        self.message = message or frappe._("Invalid Template Forking")
        self.data = frappe._dict(
            notification_template=template
        )


class NotificationTemplate(Document):
    key: str
    subject: str
    content: str
    is_fork_of: str
    lang: str
    last_used_on: str
    last_used_by: str
    created_by: str
    allowed_clients: List[NotificationClientItem]
    lang_templates: List[NotificationTemplateLanguageItem]
    channel_senders: List[NotificationTemplateSenderItem]

    def autoname(self):
        """
        - Client name already includes manager name
        """
        client = self.created_by or get_active_notification_client()
        if not client:
            raise NotificationClientNotFound()

        self.name = frappe.scrub(f"{client}-{self.key}").replace("_", "-")

    def before_insert(self):
        client = self.created_by or get_active_notification_client()
        if client:
            self.created_by = client

    def validate(self):
        if not self.lang:
            self.lang = "en"
        self.validate_allowed_clients()
        self.validate_language_templates()

    def fork(self) -> "NotificationTemplate":
        """
        - Validate & Fork
        - Forking = Duplicate current template & add entry in Notification Client
        """
        self.validate_can_fork()

        client = get_active_notification_client()
        d = NotificationTemplate(dict(self.as_dict()))
        d.created_by = client
        d.is_fork_of = self.name
        d.name = None
        d.allowed_clients = []

        d.insert(ignore_permissions=True)

        client = frappe.get_doc("Notification Client", client)
        client.append("custom_templates", dict(key=self.key, template=d.name))
        client.save(ignore_permissions=True)

        return d

    def validate_can_fork(self):
        """
        Forking is allowed if
        - This is not a fork of another template
        - This template belongs to a ClientManager who is the manager for current Client
        """
        if self.is_fork_of:
            raise InvalidTemplateForking(
                template=self.name,
                message=frappe._("Template {0} is a fork of {1}").format(self.name, self.is_fork_of)
            )

        if not self.is_created_by_client_manager():
            raise InvalidTemplateForking(
                template=self.name,
                message=frappe._("Template {0} has been created by non manager: {1}").format(
                    self.name, self.created_by
                )
            )

        client = get_active_notification_client()
        if not client:
            raise NotificationClientNotFound()

        if client == self.created_by:
            raise InvalidTemplateForking(
                template=self.name,
                message=frappe._("You cannot fork a template created by yourself")
            )

        client_manager = frappe.db.get_value("Notification Client", client, "managed_by")
        if client_manager != self.created_by:
            raise InvalidTemplateForking(
                template=self.name,
                message=frappe._("You can only fork templates created by your manager")
            )

        return True

    def validate_allowed_clients(self):
        """
        Notification Templates created_by ClientManager can only be shared with subordinate-clients
        """
        if not len(self.allowed_clients):
            return

        # Verify the owner is actually a ClientManager
        if not self.is_created_by_client_manager():
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
        """
        - Make sure the main lang is not duplicated in lang_templates[]
        - Make sure no duplicate lang exists in lang_templates
        - Remove duplicate rows
        - Remove lang_rows with empty subject & content
        """
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

    def send_notification(
            self,
            context: dict,
            recipients: List[NotificationRecipientItem]) -> NotificationOutbox:
        """
        Create Notification Outbox Document which will manage and track the procedure
        """
        # Blow the templates!
        subject, content = self.get_lang_templates(context.get("lang") or self.lang)
        subject = frappe.render_template(subject, context)
        content = frappe.render_template(content, context)

        _sender_info = dict()

        def _get_sender(channel: str):
            if channel in _sender_info:
                return _sender_info.get(channel)

            _sender_info[channel] = self.get_channel_sender(channel)
            return _sender_info[channel]

        outbox = frappe.get_doc(dict(
            doctype="Notification Outbox",
            subject=subject,
            content=content,
            client=get_active_notification_client(),
            recipients=[
                dict(
                    channel=x.get("channel"),
                    channel_id=x.get("channel_id"),
                    sender_type=_get_sender(x.get("channel"))[0],
                    sender=_get_sender(x.get("channel"))[1],
                )
                for x in recipients
            ]
        ))

        outbox.docstatus = 1
        outbox.insert(ignore_permissions=True)

        self.db_set("last_used_on", now_datetime())
        self.db_set("last_used_by", get_active_notification_client())

        return outbox

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

    def is_created_by_client_manager(self):
        """
        Returns True if self.created_by is a Client Manager
        """
        is_client_manager = frappe.db.get_value(
            "Notification Client",
            self.created_by,
            "is_client_manager") if self.created_by else False

        return bool(is_client_manager)
