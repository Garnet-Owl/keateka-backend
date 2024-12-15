from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.database import get_db
from app.features.auth.dependencies import get_current_active_user
from app.features.notifications import schemas
from app.features.notifications.service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/", response_model=List[schemas.NotificationResponse])
async def get_notifications(
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's notifications."""
    service = NotificationService(db)
    return await service.get_user_notifications(current_user.id, skip, limit)


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    service = NotificationService(db)
    notification = await service.mark_as_read(notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification marked as read"}
