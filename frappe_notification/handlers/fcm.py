import frappe

from renovation_core.utils.fcm import _notify_via_fcm
from frappe_notification import NotificationOutbox, NotificationOutboxStatus


def fcm_handler(
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
    # If there is any extra arguments, eg: user_identifier
    **kwargs
):
    assert channel == "FCM"

    if to_validate:
        # TODO: We could make use of Firebase Library ?
        return True

    outbox: NotificationOutbox = frappe.get_doc("Notification Outbox", outbox)
    try:
        if not frappe.flags.in_test:
            _notify_via_fcm(
                title=subject,
                body=content,
                data=None,
                tokens=[
                    channel_id
                ]
            )

        outbox.update_status(outbox_row_name, NotificationOutboxStatus.SUCCESS)
    except BaseException:
        outbox.update_status(outbox_row_name, NotificationOutboxStatus.FAILED)
