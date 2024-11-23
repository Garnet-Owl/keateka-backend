from typing import Optional, Dict, Any

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings


class NotificationService:
    def __init__(self):
        # Initialize Firebase Admin SDK
        if not settings.FIREBASE_CREDENTIALS_PATH:
            raise ValueError("Firebase credentials path not set")

        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        except ValueError:
            # App already initialized
            pass

    def send_notification(
        self, token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a Firebase Cloud Message to a specific device

        Args:
            token: The FCM token of the device
            title: Notification title
            body: Notification body
            data: Optional data payload
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                token=token,
            )

            response = messaging.send(message)
            print(f"Successfully sent message: {response}")
            return True

        except Exception as e:
            print(f"Error sending notification: {str(e)}")
            return False

    def send_multicast(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a Firebase Cloud Message to multiple devices
        """
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                tokens=tokens,
            )

            response = messaging.send_multicast(message)

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            }

        except Exception as e:
            print(f"Error sending multicast notification: {str(e)}")
            return {"success_count": 0, "failure_count": len(tokens)}

    def send_topic_message(
        self, topic: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a Firebase Cloud Message to a topic
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                topic=topic,
            )

            response = messaging.send(message)
            print(f"Successfully sent message to topic: {response}")
            return True

        except Exception as e:
            print(f"Error sending topic message: {str(e)}")
            return False

    @staticmethod
    def subscribe_to_topic(token: str, topic: str) -> bool:
        """
        Subscribe a device to a topic
        """
        try:
            response = messaging.subscribe_to_topic(token, topic)
            print(f"Successfully subscribed to topic: {response.success_count} tokens")
            return True

        except Exception as e:
            print(f"Error subscribing to topic: {str(e)}")
            return False

    @staticmethod
    def unsubscribe_from_topic(token: str, topic: str) -> bool:
        """
        Unsubscribe a device from a topic
        """
        try:
            response = messaging.unsubscribe_from_topic(token, topic)
            print(
                f"Successfully unsubscribed from topic: {response.success_count} tokens"
            )
            return True

        except Exception as e:
            print(f"Error unsubscribing from topic: {str(e)}")
            return False


# Create a singleton instance
notification_service = NotificationService()
