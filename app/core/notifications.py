from typing import Optional, Dict
from app.services.notifications import notification_service
from app.database import get_db
from app.models.user import User


def send_notification(
    user_id: int, title: str, body: str, data: Optional[Dict[str, str]] = None
) -> bool:
    """
    Send notification to a user by their ID

    Args:
        user_id: ID of the user to notify
        title: Notification title
        body: Notification message
        data: Optional data payload

    Returns:
        bool: True if notification was sent successfully
    """
    try:
        # Get database session
        db = next(get_db())

        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.fcm_token:
            return False

        # Send notification using the service
        return notification_service.send_notification(
            token=user.fcm_token, title=title, body=body, data=data
        )
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return False


def send_bulk_notification(
    user_ids: list[int],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    """
    Send notification to multiple users

    Args:
        user_ids: List of user IDs to notify
        title: Notification title
        body: Notification message
        data: Optional data payload

    Returns:
        Dict with success and failure counts
    """
    try:
        # Get database session
        db = next(get_db())

        # Get users' FCM tokens
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        tokens = [user.fcm_token for user in users if user.fcm_token]

        if not tokens:
            return {"success_count": 0, "failure_count": len(user_ids)}

        # Send notifications using the service
        return notification_service.send_multicast(
            tokens=tokens, title=title, body=body, data=data
        )
    except Exception as e:
        print(f"Error sending bulk notification: {str(e)}")
        return {"success_count": 0, "failure_count": len(user_ids)}
