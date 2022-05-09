import frappe
from frappe_notification import NotificationOutboxStatus, NotificationOutbox


def email_handler(
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
    assert channel == "Email"
    assert sender_type in ("Email Account", None)

    if to_validate:
        return True

    outbox: NotificationOutbox = frappe.get_doc("Notification Outbox", outbox)
    try:
        if not frappe.flags.in_test:
            frappe.sendmail(
                recipients=[channel_id],
                subject=subject,
                content=content,
                sender=sender,
            )

        outbox.update_status(outbox_row_name, NotificationOutboxStatus.SUCCESS)
    except BaseException:
        outbox.update_status(outbox_row_name, NotificationOutboxStatus.FAILED)
