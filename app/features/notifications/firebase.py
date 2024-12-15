import firebase_admin
from firebase_admin import messaging, credentials
from typing import Dict, Any, Optional
from app.shared.config import settings
from app.features.notifications.exceptions import NotificationError


class FirebaseHandler:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialize_firebase()
            FirebaseHandler._initialized = True

    @staticmethod
    def _initialize_firebase():
        """Initialize Firebase Admin SDK."""
        if settings.FIREBASE_CREDENTIALS_PATH:
            try:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            except ValueError:
                # App already initialized
                pass
            except Exception as e:
                raise NotificationError(f"Firebase initialization failed: {str(e)}")

    @staticmethod
    async def send_push_notification(
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Send push notification using Firebase."""
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data,
                token=token,
            )
            return messaging.send(message)
        except Exception as e:
            raise NotificationError(f"Push notification failed: {str(e)}")
