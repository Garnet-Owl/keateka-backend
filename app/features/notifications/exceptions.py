from typing import Optional, Dict, Any
from app.shared.exceptions import BaseAPIException


class NotificationError(BaseAPIException):
    def __init__(
        self,
        message: str = "Notification error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="NOTIFICATION_ERROR",
            details=details,
        )
