from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Awaitable, Callable

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self) -> None:
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        self.connection_handlers: dict[str, set[Callable[[str, dict], Awaitable[None]]]] = {}

    async def connect(self, websocket: WebSocket, client_id: str, group: str = "default") -> None:
        """Accept and store a WebSocket connection."""
        await websocket.accept()

        if group not in self.active_connections:
            self.active_connections[group] = {}

        self.active_connections[group][client_id] = websocket
        logger.info("Client %s connected to group %s", client_id, group)  # Changed to use logging format

    async def disconnect(self, client_id: str, group: str = "default") -> None:
        """Remove a WebSocket connection."""
        if group in self.active_connections:
            self.active_connections[group].pop(client_id, None)
            if not self.active_connections[group]:
                self.active_connections.pop(group)
        logger.info("Client %s disconnected from group %s", client_id, group)  # Changed to use logging format

    async def send_personal_message(self, message: dict, client_id: str, group: str = "default") -> None:
        """Send a message to a specific client."""
        if group in self.active_connections and client_id in self.active_connections[group]:
            websocket = self.active_connections[group][client_id]
            await websocket.send_json(
                {
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "data": message,
                }  # Fixed to timezone-aware timestamp
            )

    async def broadcast(
        self,
        message: dict,
        group: str = "default",
        exclude: str | None = None,
    ) -> None:
        """Broadcast a message to all clients in a group."""
        if group in self.active_connections:
            for client_id, websocket in self.active_connections[group].items():
                if client_id != exclude:
                    try:
                        await websocket.send_json(
                            {
                                "timestamp": datetime.now(
                                    tz=timezone.utc
                                ).isoformat(),  # Fixed to timezone-aware timestamp
                                "data": message,
                            }
                        )
                    except WebSocketDisconnect:
                        await self.disconnect(client_id, group)

    def register_handler(self, event_type: str, handler: Callable[[str, dict], Awaitable[None]]) -> None:
        """Register a handler for specific event types."""
        if event_type not in self.connection_handlers:
            self.connection_handlers[event_type] = set()
        self.connection_handlers[event_type].add(handler)

    async def handle_incoming_message(self, client_id: str, message: str) -> None:
        """Process incoming WebSocket messages."""
        try:
            data = json.loads(message)
            event_type = data.get("type")

            if event_type and event_type in self.connection_handlers:
                for handler in self.connection_handlers[event_type]:
                    await handler(client_id, data)
            else:
                logger.warning("No handler for event type: %s", event_type)  # Changed to use logging format

        except json.JSONDecodeError:
            logger.exception("Invalid JSON received from client %s", client_id)  # Changed to use logging format
        except Exception:  # Removed e
            logger.exception(
                "Error processing message from client %s",
                client_id,  # Changed to use logging format
            )


# WebSocket Authentication Middleware
class WebSocketAuthMiddleware:
    """Middleware for WebSocket authentication."""

    def __init__(self, auth_handler: Callable[[dict], Awaitable[bool]]) -> None:
        self.auth_handler = auth_handler

    async def authenticate(self, websocket: WebSocket) -> bool:
        """
        Authenticate WebSocket connection.

        Args:
            websocket: The WebSocket connection to authenticate

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Get auth token from query parameters or headers
            token = websocket.query_params.get("token") or websocket.headers.get("Authorization", "").replace(
                "Bearer ", ""
            )

            if not token:
                return False

            # Verify token using provided auth handler
            is_authenticated = await self.auth_handler({"token": token})

        except Exception:  # Removed e
            logger.exception("WebSocket authentication error")  # Changed to use logging format
            return False
        else:
            return is_authenticated
