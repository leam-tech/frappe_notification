# Add your own Channel

FrappeNotifications App allows you to add your own custom notification channel. For eg. `Telegram`

- Create a new `Notification Channel` entry: `Telegram`
- Add hook
  ```py
  notification_channel_handler = {
    "Telegram": "your_app.notification_handlers.telegram_handler"
  }
  ```
- Create your python handler `your_app.notification_handlers.telegram_handler`  
  The arguments would be:
  ```py
  def telegram_handler(
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
    # When this is true, verify the channel_id & other params. Do not send the message
    to_validate=False,
    # The name of Notification Outbox
    outbox: str,
    # The name of the child row in Notification Outbox
    outbox_row_name: str,
  ):
    """
    Things todo here:
    - if to_validate is True, do not send notification. Raise error if you have any issues in validations
    - Send out the notification otherwise
    - Update the outbox.outbox_row_name status with
        frappe.get_doc("Notification Outbox", outbox).update_recipient_status(dict(outbox_row_name=NotificationOutboxStatus.SUCCESS))
    """
    pass
  ```
