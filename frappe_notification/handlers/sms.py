import frappe
from frappe_notification import (
    FrappeNotificationException,
    NotificationOutbox,
    NotificationOutboxStatus)
from renovation_core.utils.sms_setting import validate_receiver_nos, send_sms


def sms_handler(
    *,
    # The channel selected, ie Telegram
    channel: str,
    # The Sender Type, for eg. TelegramBot
    sender_type: str,
    # The Sender, TelegramBot.bot_a
    sender: str,
    # Recipient ID, @test-user-a
    channel_id: str,
    # Subject of message, ignore for Telegram, useful for Email
    subject: str,
    # The text message content
    content: str,
    # The name of Notification Outbox
    outbox: str,
    # The name of the child row in Notification Outbox
    outbox_row_name: str,
    # When this is true, verify the channel_id & other params. Do not send the message
    to_validate=False,
):
    assert channel == "SMS"
    assert sender_type is None
    assert sender is None

    if to_validate:
        if frappe.flags.in_test:
            # No validations in_test
            return
        try:
            validate_receiver_nos([channel_id])
        except BaseException:
            raise FrappeNotificationException(
                message=frappe._("SMS Receiver number is invalid"),
                error_code="INVALID_SMS_NUMBER",
                data=frappe._dict(
                    number=channel_id
                ))
        return

    outbox: NotificationOutbox = frappe.get_doc("Notification Outbox", outbox)
    try:
        if not frappe.flags.in_test:
            send_sms([channel_id], msg=content, success_msg=False)

        outbox.update_status(outbox_row_name, NotificationOutboxStatus.SUCCESS)
    except BaseException:
        outbox.update_status(outbox_row_name, NotificationOutboxStatus.FAILED)
