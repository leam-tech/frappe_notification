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
