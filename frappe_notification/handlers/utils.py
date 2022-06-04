import frappe


def log_handler_error(
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
    return frappe.log_error(
        title=f"Handler Error: {channel}",
        message=f"""
Channel: {channel}
Channel ID: {channel_id}
Sender Type: {sender_type}
Sender: {sender}

Subject: {subject}
Content: {content}
Outbox: {outbox}
Outbox Row Name: {outbox_row_name}
To Validate: {to_validate}

kwargs: {kwargs}

Traceback:
{frappe.get_traceback()}
"""
    )
