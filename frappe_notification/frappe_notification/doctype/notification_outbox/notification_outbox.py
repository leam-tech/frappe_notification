# Copyright (c) 2022, Leam Technology Systems and contributors
# For license information, please see license.txt
from typing import List, Dict, Callable, Optional, Tuple, Union
from enum import Enum

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

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


class RecipientsBatchItem(frappe._dict):
    outbox_row_name: str
    user_identifier: str
    channel_id: str


class RecipientsBatch(frappe._dict):
    channel: str
    channel_args: str
    sender_type: str
    sender: str
    recipients: List[RecipientsBatchItem]


class ChannelHandlerParamsBase(frappe._dict):
    channel: str
    channel_args: dict
    sender: str
    sender_type: str
    to_validate: bool

    outbox: str
    content: str
    subject: str


class ChannelHandlerParams(ChannelHandlerParamsBase):
    channel_id: str
    user_identifier: Optional[str]
    outbox_row_name: str


class ChannelHandlerParamsBatched(ChannelHandlerParamsBase):
    recipients: List[RecipientsBatchItem]


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
        recipients = self.get_batched_recipients()
        for r in recipients:
            params = _get_channel_handler_invoke_params(self, r)
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

        def _process_exc(params: ChannelHandlerParams, err):
            err = err.as_dict() if isinstance(err, FrappeNotificationException) else frappe._dict(
                message=str(err), error_code="UNKNOWN_ERROR")

            err.update(dict(params))
            return err

        for row in self.recipients:
            params = _get_channel_handler_invoke_params(self, row)
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

    def update_recipient_status(self, recipient_status: Dict[str, NotificationOutboxStatus]):
        """
        Update the OutboxItem status & the status of the Outbox itself
        """
        if self.docstatus != 1:
            return

        has_update = False
        for r in self.recipients:
            if r.name not in recipient_status:
                continue

            if r.status == recipient_status[r.name].value:
                continue

            has_update = True
            r.status = recipient_status[r.name].value
            if r.status == NotificationOutboxStatus.SUCCESS.value:
                r.time_sent = now_datetime()

        if not has_update:
            return

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

    def get_batched_recipients(
            self
    ) -> List[Union[NotificationOutboxRecipientItem, RecipientsBatch]]:
        """
        Batch similar Recipients together.
        Batching rules:
        - Same Channel
        - Same Channel Args
        """
        supported_channels = {
            x.name: x.batch_recipients_size or 5
            for x in frappe.get_all(
                "Notification Channel",
                dict(batch_recipients=1))
        }

        batches = []
        active_batch = dict()

        def _finalize_active_batch(k: Tuple[str, str]):
            _batch = active_batch[k]
            del _batch["count"]
            del active_batch[k]

            batches.append(RecipientsBatch(dict(
                channel=k[0],
                channel_args=k[1],
                sender_type=k[2],
                sender=k[3],
                channel_ids=_batch,
            )))

        for r in self.recipients:
            if r.status is None:
                r.status = NotificationOutboxStatus.PENDING.value
            if r.status != NotificationOutboxStatus.PENDING.value:
                continue

            if r.channel not in supported_channels:
                # Add back as normal Recipient Item
                batches.append(r)
                continue

            k = (r.channel, r.channel_args, r.sender_type, r.sender_type)
            _batch_item: dict = active_batch.setdefault(k, frappe._dict(count=0))
            _user_identifier: list = _batch_item.setdefault(r.user_identifier, [])
            _user_identifier.append(r.channel_id)
            _batch_item.count += 1

            if _batch_item.count >= supported_channels[r.channel]:
                # Current batch is full. Wrap it up and let's reset.
                _finalize_active_batch(k)

        # Finalize incomplete batches
        for k in list(active_batch.keys()):
            _finalize_active_batch(k)

        return batches


def _get_channel_handler_invoke_params(
    outbox: NotificationOutbox,
    recipient: Union[NotificationOutboxRecipientItem, RecipientsBatch]
):
    channel_args = recipient.channel_args
    if isinstance(channel_args, str):
        channel_args = frappe.parse_json(channel_args)

    if not channel_args:
        channel_args = dict()

    _common = dict(
        channel_args=channel_args,
        channel=recipient.get("channel"),
        sender=recipient.get("sender"),
        sender_type=recipient.get("sender_type"),
        subject=outbox.get("subject"),
        content=outbox.get("content"),
        outbox=outbox.name,
        to_validate=False,
    )

    if isinstance(recipient, RecipientsBatch):
        return ChannelHandlerParamsBatched(dict(
            **_common,
            recipients=recipient.recipients,
        ))

    return ChannelHandlerParams(dict(
        **_common,
        channel_id=recipient.get("channel_id"),
        user_identifier=recipient.get("user_identifier"),
        outbox_row_name=recipient.get("name"),
    ))
