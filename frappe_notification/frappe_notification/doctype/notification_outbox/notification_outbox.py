# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt
from typing import List, Dict, Callable, Optional, Union
from enum import Enum

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


class NotificationOutboxStatus(Enum):
    SUCCESS = "Success"
    PENDING = "Pending"
    FAILED = "Failed"
    PARTIAL_SUCCESS = "Partial Success"


class ChannelHandlerInvokeParams(frappe._dict):
    channel: str
    channel_id: str
    channel_args: dict
    user_identifier: Optional[str]

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

    _channel_handlers: Dict[str, Callable] = None

    def validate(self):
        """ All validations kick in on_submit """
        pass

    def before_submit(self):
        self.status = NotificationOutboxStatus.PENDING.value
        for row in self.recipients:
            row.status = NotificationOutboxStatus.PENDING.value

    def on_submit(self):
        self.validate_recipient_channel_ids()
        self.send_pending_notifications()

    def send_pending_notifications(self):
        for row in self.recipients:
            if NotificationOutboxStatus(row.status) != NotificationOutboxStatus.PENDING:
                continue

            params = self._get_channel_handler_invoke_params(row)
            fn = self.get_channel_handler(params.channel)
            fn.fnargs = params.keys()  # please check frappe.call implementation

            frappe.enqueue(
                fn,
                enqueue_after_commit=True,
                now=frappe.flags.in_test,
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
            err = err.as_dict() if isinstance(err, FrappeNotificationException) else frappe._dict(
                message=str(err), error_code="UNKNOWN_ERROR")

            err.update(dict(params))
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
        if self._channel_handlers is None:
            self._channel_handlers = dict()

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

        if isinstance(handler, (list, tuple)):
            handler = handler[0]
        if isinstance(handler, str):
            handler = frappe.get_attr(handler)

        if not handler:
            return _set_handler(NotificationChannelHandlerNotFound(channel=channel))

        return _set_handler(handler)

    def update_status(self, outbox_row_name: str, status: NotificationOutboxStatus):
        """
        Update the OutboxItem status & the status of the Outbox itself
        """
        if self.docstatus != 1:
            return

        row = self.get("recipients", {"name": outbox_row_name})
        if not row:
            return

        row = row[0]
        if NotificationOutboxStatus(row.status) == status:
            return

        # Update row status
        row.status = status.value

        # Update Outbox Status
        row_statuses = set([NotificationOutboxStatus(x.status) for x in self.recipients])
        if NotificationOutboxStatus.PENDING in row_statuses:
            self.status = NotificationOutboxStatus.PENDING.value
        elif len(row_statuses) == 1:
            self.status = row_statuses.pop().value
        else:
            self.status = NotificationOutboxStatus.PARTIAL_SUCCESS.value

        self.flags.ignore_validate_update_after_submit = True
        self.save(ignore_permissions=True)

    def _get_channel_handler_invoke_params(self, row: NotificationOutboxRecipientItem):
        channel_args = row.channel_args
        if isinstance(channel_args, str):
            channel_args = frappe.parse_json(channel_args)

        if not channel_args:
            channel_args = dict()

        return ChannelHandlerInvokeParams(dict(
            channel=row.get("channel"),
            channel_id=row.get("channel_id"),
            channel_args=channel_args,
            user_identifier=row.get("user_identifier"),
            sender=row.get("sender"),
            sender_type=row.get("sender_type"),
            subject=self.get("subject"),
            content=self.get("content"),
            to_validate=False,
            outbox=self.name,
            outbox_row_name=row.get("name"),
        ))
