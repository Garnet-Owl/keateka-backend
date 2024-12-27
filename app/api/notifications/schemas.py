from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class NotificationBase(BaseModel):
    title: str
    body: str
    type: str
    data: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    status: str
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
