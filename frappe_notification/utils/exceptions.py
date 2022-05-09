from typing import List, Optional

import frappe


class FrappeNotificationException(Exception):
    """
    FrappeNotification Exceptions Base Class
    """
    error_code: str
    message: str
    data: dict = frappe._dict()
    http_status_code: int = 500

    def __init__(self, error_code: str = None, message: str = None, data: dict = None) -> None:
        super().__init__(None)
        self.error_code = error_code
        self.message = message
        self.data = data

    def as_dict(self):
        return frappe._dict(
            message=self.message,
            error_code=self.error_code,
            **self.data,
        )


class ValidationError(FrappeNotificationException):
    def __init__(self, message: str):
        self.error_code = "VALIDATION_ERROR"
        self.message = message or frappe._("Validation Error")
        self.data = dict()


class PermissionDenied(FrappeNotificationException):
    def __init__(self, message: str = None, **kwargs):
        self.error_code = "PERMISSION_DENIED"
        self.http_status_code = 403
        self.data = frappe._dict(
            **kwargs
        )


class RecipientErrors(FrappeNotificationException):
    def __init__(self, recipient_errors: List[FrappeNotificationException]) -> None:
        self.error_code = "NOTIFICATION_RECEIVER_ERRORS"
        self.message = frappe._("There are errors with the receivers mentioned")
        self.data = frappe._dict(
            recipient_errors=[
                x.as_dict() if isinstance(x, FrappeNotificationException) else x
                for x in recipient_errors]
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


class NotificationChannelDisabled(FrappeNotificationException):
    def __init__(self, channel: str) -> None:
        self.error_code = "NOTIFICATION_CHANNEL_DISABLED"
        self.message = frappe._("Notification Channel is Disabled")
        self.http_status_code = 400
        self.data = frappe._dict(channel=channel)


class NotificationChannelHandlerNotFound(FrappeNotificationException):
    def __init__(self, channel: str) -> None:
        self.error_code = "NOTIFICATION_CHANNEL_HANDLER_NOT_FOUND"
        self.message = frappe._("Notification Channel Handler not found")
        self.http_status_code = 400
        self.data = frappe._dict(channel=channel)


class ActionRestrictedToClientManager(FrappeNotificationException):
    def __init__(self) -> None:
        self.error_code = "ACTION_RESTRICTED_TO_CLIENT_MANAGER_ONLY"
        self.message = frappe._("Only Manager can perform this action")
        self.http_status_code = 400


class NotificationTemplateNotFound(FrappeNotificationException):
    def __init__(self, template: Optional[str] = None):
        self.error_code = "NOTIFICATION_TEMPLATE_NOT_FOUND"
        self.message = frappe._("Notification Template not found")
        self.http_status_code = 404
        self.data = frappe._dict(
            template=template
        )
