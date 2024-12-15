from typing import Dict
from fastapi import WebSocket
from app.shared.middleware.websocket import WebSocketConnectionManager


class JobWebSocketManager:
    def __init__(self):
        self.connection_manager = WebSocketConnectionManager()

    async def connect_client(self, websocket: WebSocket, job_id: int, user_id: str):
        """Connect a client to a job's WebSocket."""
        group = f"job_{job_id}"
        await self.connection_manager.connect(websocket, str(user_id), group)

    async def disconnect_client(self, job_id: int, user_id: str):
        """Disconnect a client from a job's WebSocket."""
        group = f"job_{job_id}"
        await self.connection_manager.disconnect(str(user_id), group)

    async def broadcast_status_update(self, job_id: int, status_data: Dict):
        """Broadcast job status update to all connected clients."""
        group = f"job_{job_id}"
        await self.connection_manager.broadcast({"type": "status_update", "data": status_data}, group)

    async def broadcast_tracking_update(self, job_id: int, tracking_data: Dict):
        """Broadcast tracking update to all connected clients."""
        group = f"job_{job_id}"
        await self.connection_manager.broadcast({"type": "tracking_update", "data": tracking_data}, group)

    async def send_cleaner_notification(self, job_id: int, cleaner_id: str, data: Dict):
        """Send notification to specific cleaner."""
        group = f"job_{job_id}"
        await self.connection_manager.send_personal_message(
            {"type": "cleaner_notification", "data": data},
            str(cleaner_id),
            group,
        )
