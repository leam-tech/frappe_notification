# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt
from typing import List, Dict, Callable, Union

import frappe
from frappe.model.document import Document

from frappe_notification import (
    NotificationChannelHandlerNotFound,
    NotificationChannelDisabled,
    NotificationChannelNotFound,
    RecipientErrors)
from frappe_notification.utils.exceptions import FrappeNotificationException

from ..notification_outbox_recipient_item.notification_outbox_recipient_item import \
    NotificationOutboxRecipientItem


class ChannelHandlerInvokeParams(frappe._dict):
    channel: str
    channel_id: str
    sender: str
    sender_type: str
    to_validate: bool

    outbox: str
    outbox_row_name: str

    content: str
    subject: str


HOOK_NOTIFICATION_CHANNEL_HANDLER = "notification_channel_handler"


class NotificationOutbox(Document):
    """
    Each Notification Channel has to define a Handler
    It will be invoked at two instances:
    - While making an Outbox entry, with for_validate=True
        - The handler could make sure the recipient details are valid in the validation phase
    - While actually triggering the notification in a background job
        - The handler is responsible in updating the status of the Outbox Item

    - This document can be extended to include support for retrying failed notifications
    """
    subject: str
    content: str
    notification_client: str
    status: str
    recipients: List[NotificationOutboxRecipientItem]

    _channel_handlers: Dict[str, Callable] = dict()

    def validate(self):
        """ All validations kick in on_submit """
        pass

    def on_submit(self):
        self.validate_recipient_channel_ids()
        self.send_pending_notifications()

    def send_pending_notifications(self):
        for row in self.recipients:
            params = self._get_channel_handler_invoke_params(row)
            frappe.enqueue(
                self.get_channel_handler(params.channel),
                enqueue_after_commit=True,
                is_async=not frappe.flags.in_test,
                **params
            )

    def validate_recipient_channel_ids(self):
        """
        1st Phase Handler Invocation
        Handlers can validate if it can do well with the params specified
        If any one handler stands back, none of the notifications get sent
        """
        errors = []

        def _process_exc(params: ChannelHandlerInvokeParams, err):
            err = err.as_dict() if isinstance(err, FrappeNotificationException) else dict(
                exc=str(err), data=dict())

            err.data.update(**params)
            return err

        for row in self.recipients:
            params = self._get_channel_handler_invoke_params(row)
            params.to_validate = True

            handler = self.get_channel_handler(params.channel)
            if not callable(handler):
                errors.append(_process_exc(params, handler))
                continue

            try:
                handler(**params)
            except BaseException as e:
                errors.append(_process_exc(params, e))

        if len(errors):
            raise RecipientErrors(recipient_errors=errors)

    def get_channel_handler(self, channel: str) -> Union[Callable, FrappeNotificationException]:
        """
        Gets the channel handler or Exception instance where applicable
        """
        if channel in self._channel_handlers:
            return self._channel_handlers.get(channel)

        def _set_handler(handler):
            self._channel_handlers[channel] = handler
            return handler

        if not frappe.db.exists("Notification Channel", channel):
            return _set_handler(NotificationChannelNotFound(channel=channel))

        if not frappe.db.get_value("Notification Channel", channel, "enabled"):
            return _set_handler(NotificationChannelDisabled(channel=channel))

        handler = frappe.get_hooks(HOOK_NOTIFICATION_CHANNEL_HANDLER, dict()).get(channel)
        if not handler:
            return _set_handler(NotificationChannelHandlerNotFound(channel=channel))

        if isinstance(handler, str):
            handler = frappe.get_attr(handler)

        return _set_handler(handler)

    def _get_channel_handler_invoke_params(self, row: NotificationOutboxRecipientItem):
        return ChannelHandlerInvokeParams(dict(
            channel=row.get("channel"),
            sender=row.get("sender"),
            sender_type=row.get("sender_type"),
            channel_id=row.get("channel_id"),
            subject=self.get("subject"),
            content=self.get("content"),
            to_validate=False,
            outbox=self.name,
            outbox_row_name=row.get("name"),
        ))
