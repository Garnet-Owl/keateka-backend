from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.jobs.models import JobStatus


class JobEventType(str, Enum):
    CREATED = "job_created"
    SCHEDULED = "job_scheduled"
    STARTED = "job_started"
    COMPLETED = "job_completed"
    PAID = "job_paid"
    CANCELED = "job_canceled"


class JobEvent(BaseModel):
    """Event model for job status changes."""

    event_type: JobEventType
    job_id: UUID
    client_id: UUID
    cleaner_id: Optional[UUID] = None
    status: JobStatus
    timestamp: float = Field(default_factory=lambda: __import__("time").time())
    data: Dict[str, Any] = {}


class JobEventPublisher:
    """Handles publishing of job-related events."""

    def __init__(self, redis_client=None, websocket_manager=None, notification_service=None):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.notification_service = notification_service

    async def publish_job_created(self, job_id: UUID, client_id: UUID) -> None:
        """Publish a job created event."""
        event = JobEvent(
            event_type=JobEventType.CREATED,
            job_id=job_id,
            client_id=client_id,
            status=JobStatus.PENDING,
            data={"message": "New job has been created"},
        )
        await self._publish(event)

    async def publish_job_scheduled(self, job_id: UUID, client_id: UUID, cleaner_id: UUID, scheduled_time: str) -> None:
        """Publish a job scheduled event."""
        event = JobEvent(
            event_type=JobEventType.SCHEDULED,
            job_id=job_id,
            client_id=client_id,
            cleaner_id=cleaner_id,
            status=JobStatus.SCHEDULED,
            data={"message": "Job has been scheduled", "scheduled_time": scheduled_time},
        )
        await self._publish(event)

    async def publish_job_started(self, job_id: UUID, client_id: UUID, cleaner_id: UUID) -> None:
        """Publish a job started event."""
        event = JobEvent(
            event_type=JobEventType.STARTED,
            job_id=job_id,
            client_id=client_id,
            cleaner_id=cleaner_id,
            status=JobStatus.IN_PROGRESS,
            data={"message": "Job has started"},
        )
        await self._publish(event)

    async def publish_job_completed(
        self, job_id: UUID, client_id: UUID, cleaner_id: UUID, duration: int, cost: float
    ) -> None:
        """Publish a job completed event."""
        event = JobEvent(
            event_type=JobEventType.COMPLETED,
            job_id=job_id,
            client_id=client_id,
            cleaner_id=cleaner_id,
            status=JobStatus.COMPLETED,
            data={"message": "Job has been completed", "duration_minutes": duration, "cost": cost},
        )
        await self._publish(event)

    async def publish_job_paid(self, job_id: UUID, client_id: UUID, cleaner_id: UUID, amount: float) -> None:
        """Publish a job paid event."""
        event = JobEvent(
            event_type=JobEventType.PAID,
            job_id=job_id,
            client_id=client_id,
            cleaner_id=cleaner_id,
            status=JobStatus.PAID,
            data={"message": "Payment received for job", "amount": amount},
        )
        await self._publish(event)

    async def publish_job_canceled(
        self, job_id: UUID, client_id: UUID, cleaner_id: Optional[UUID], reason: str
    ) -> None:
        """Publish a job canceled event."""
        event = JobEvent(
            event_type=JobEventType.CANCELED,
            job_id=job_id,
            client_id=client_id,
            cleaner_id=cleaner_id,
            status=JobStatus.CANCELED,
            data={"message": "Job has been canceled", "reason": reason},
        )
        await self._publish(event)

    async def _publish(self, event: JobEvent) -> None:
        """
        Publish event to all necessary channels:
        1. Redis pub/sub for internal service communication
        2. WebSockets for real-time client updates
        3. Push notifications for mobile clients

        This implementation is a placeholder. In a real application,
        these would be implemented with actual external services.
        """
        event_data = event.model_dump()

        # Publish to Redis channel if available
        if self.redis_client:
            channel = f"jobs:{event.event_type}"
            try:
                await self.redis_client.publish(channel, event_data)
            except Exception as e:
                print(f"Error publishing to Redis: {e}")

        # Send to WebSocket connections if available
        if self.websocket_manager:
            try:
                # Send to specific client connection
                await self.websocket_manager.send_to_user(user_id=str(event.client_id), message=event_data)

                # If there's a cleaner, send to them too
                if event.cleaner_id:
                    await self.websocket_manager.send_to_user(user_id=str(event.cleaner_id), message=event_data)
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")

        # Send push notification if service available
        if self.notification_service:
            try:
                # Map event types to notification priorities
                priority = (
                    "high"
                    if event.event_type in [JobEventType.STARTED, JobEventType.COMPLETED, JobEventType.CANCELED]
                    else "normal"
                )

                # Send to client
                await self.notification_service.send(
                    user_id=event.client_id,
                    title=f"Job {event.event_type.value.replace('_', ' ')}",
                    body=event.data.get("message", "Job status updated"),
                    data={"job_id": str(event.job_id), "type": event.event_type},
                    priority=priority,
                )

                # Send to cleaner if applicable
                if event.cleaner_id:
                    await self.notification_service.send(
                        user_id=event.cleaner_id,
                        title=f"Job {event.event_type.value.replace('_', ' ')}",
                        body=event.data.get("message", "Job status updated"),
                        data={"job_id": str(event.job_id), "type": event.event_type},
                        priority=priority,
                    )
            except Exception as e:
                print(f"Error sending push notification: {e}")

        # For development/debugging: print the event
        print(f"Job Event: {event.event_type} - Job: {event.job_id}")
