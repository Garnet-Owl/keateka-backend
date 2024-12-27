from datetime import datetime, timezone
from typing import Optional, Dict, Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.api.auth.models import User
from app.api.notifications import models
from app.api.notifications.exceptions import NotificationError
from app.api.notifications.firebase import FirebaseHandler
from app.api.shared.config import settings


class NotificationServiceError:
    USER_NOT_FOUND = "User not found"
    FCM_TOKEN_NOT_FOUND = "User FCM token not found"
    EMAIL_NOT_FOUND = "User email not found"
    PHONE_NOT_FOUND = "User phone number not found"
    UNSUPPORTED_TYPE = "Unsupported notification type"


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.firebase = FirebaseHandler()

    async def send_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        notification_type: str = models.NotificationType.PUSH,
    ) -> models.Notification:
        """Send a notification to a user."""
        notification = models.Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            data=json.dumps(data) if data else None,
            status=models.NotificationStatus.PENDING,
        )

        try:
            # Save notification record first
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)

            # Send based on type
            if notification_type == models.NotificationType.PUSH and settings.PUSH_ENABLED:
                await self._send_push_notification(notification)
            elif notification_type == models.NotificationType.EMAIL and settings.EMAIL_ENABLED:
                await self._send_email_notification(notification)
            elif notification_type == models.NotificationType.SMS and settings.SMS_ENABLED:
                await self._send_sms_notification(notification)
            else:
                raise NotificationError(NotificationServiceError.UNSUPPORTED_TYPE)

            # Update notification status
            notification.status = models.NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(notification)

            return notification

        except Exception as e:
            # Update notification status on failure if it was saved
            if notification.id:
                notification.status = models.NotificationStatus.FAILED
                notification.error_message = str(e)
                await self.db.commit()

            raise NotificationError(f"Failed to send notification: {str(e)}")

    async def _send_push_notification(self, notification: models.Notification) -> None:
        """Send push notification using Firebase."""
        user = await self._get_user(notification.user_id)
        if not user:
            raise NotificationError(NotificationServiceError.USER_NOT_FOUND)

        fcm_token = getattr(user, "fcm_token", None)
        if not fcm_token:
            raise NotificationError(NotificationServiceError.FCM_TOKEN_NOT_FOUND)

        data = json.loads(notification.data) if notification.data else None
        await self.firebase.send_push_notification(
            token=fcm_token,
            title=notification.title,
            body=notification.body,
            data=data,
        )

    async def _send_email_notification(self, notification: models.Notification) -> None:
        """Send email notification."""
        user = await self._get_user(notification.user_id)
        if not user:
            raise NotificationError(NotificationServiceError.USER_NOT_FOUND)

        if not user.email:
            raise NotificationError(NotificationServiceError.EMAIL_NOT_FOUND)

        # Implement email sending logic here

    async def _send_sms_notification(self, notification: models.Notification) -> None:
        """Send SMS notification."""
        user = await self._get_user(notification.user_id)
        if not user:
            raise NotificationError(NotificationServiceError.USER_NOT_FOUND)

        if not user.phone_number:
            raise NotificationError(NotificationServiceError.PHONE_NOT_FOUND)

        # Implement SMS sending logic here

    async def _get_user(self, user_id: int) -> Optional[User]:
        """Get user details."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_notifications(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[models.Notification]:
        """Get user's notifications."""
        result = await self.db.execute(
            select(models.Notification)
            .filter(models.Notification.user_id == user_id)
            .order_by(models.Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_as_read(self, notification_id: int, user_id: int) -> Optional[models.Notification]:
        """Mark notification as read."""
        notification = await self._get_notification(notification_id, user_id)
        if notification:
            notification.is_read = True
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def _get_notification(self, notification_id: int, user_id: int) -> Optional[models.Notification]:
        """Get specific notification."""
        result = await self.db.execute(
            select(models.Notification).filter(
                models.Notification.id == notification_id,
                models.Notification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """Delete a notification."""
        notification = await self._get_notification(notification_id, user_id)
        if notification:
            await self.db.delete(notification)
            await self.db.commit()
            return True
        return False
