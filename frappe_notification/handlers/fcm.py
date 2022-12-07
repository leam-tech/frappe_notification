from typing import List
import frappe

from renovation_core.utils.fcm import _notify_via_fcm
from frappe_notification import (NotificationOutbox, NotificationOutboxStatus, RecipientsBatchItem)

# FCM is a Batched Notification Channel


def fcm_handler(
    *,
    # The channel selected, ie Telegram
    channel: str,
    # Channel Specific Args, like FCM Data, Email CC
    channel_args: dict,
    # The Sender Type, for eg. TelegramBot
    sender_type: str,
    # The Sender, TelegramBot.bot_a
    sender: str,
    # Subject of message, ignore for Telegram, useful for Email
    subject: str,
    # The text message content
    content: str,
    # The name of Notification Outbox
    outbox: str,
    # Batched Items
    recipients: List[RecipientsBatchItem],
    # When this is true, verify the channel_id & other params. Do not send the message
    to_validate=False,
    # If there is any extra arguments
    ** kwargs
):
    assert channel == "FCM"

    if to_validate:
        # TODO: We could make use of Firebase Library ?
        return True

    outbox: NotificationOutbox = frappe.get_doc("Notification Outbox", outbox)
    try:
        fcm_data = None
        if channel_args and "fcm_data" in channel_args:
            fcm_data = channel_args.get("fcm_data")

        tokens = [x.channel_id for x in recipients]

        if not frappe.flags.in_test:
            _notify_via_fcm(
                title=subject,
                body=content,
                data=fcm_data,
                tokens=tokens
            )

        outbox.update_status({
            r.outbox_row_name: NotificationOutboxStatus.SUCCESS
            for r in recipients
        })
    except BaseException:
        outbox.update_status({
            r.outbox_row_name: NotificationOutboxStatus.FAILED
            for r in recipients
        })
