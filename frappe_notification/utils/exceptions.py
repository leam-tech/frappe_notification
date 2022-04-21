import frappe


class FrappeNotificationException(Exception):
    """
    FrappeNotification Exceptions Base Class
    """
    error_code: str
    message: str
    data: dict = frappe._dict()
    http_status_code: int = 500

    def __init__(self) -> None:
        super().__init__(None)

    def as_dict(self):
        return frappe._dict(
            message=self.message,
            error_code=self.error_code,
            **self.data,
        )


class NotificationClientNotFound(FrappeNotificationException):
    def __init__(self) -> None:
        self.error_code = "NOTIFICATION_CLIENT_NOT_FOUND"
        self.message = frappe._("Notification Client Not Found")
        self.http_status_code = 403


class NotificationChannelNotFound(FrappeNotificationException):
    def __init__(self, channel: str) -> None:
        self.error_code = "NOTIFICATION_CHANNEL_NOT_FOUND"
        self.message = frappe._("Notification Channel Not Found")
        self.http_status_code = 404
        self.data = frappe._dict(channel=channel)
