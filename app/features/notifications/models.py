from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.shared.database import Base, TimestampMixin


class NotificationType(str, PyEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    status = Column(String, default=NotificationStatus.PENDING)
    data = Column(String, nullable=True)  # JSON string for additional data
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
