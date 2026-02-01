"""
WebSocket handler for real-time status board updates.

Provides WebSocket endpoint for live updates on agent status,
new communications, and meeting events.
"""

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from agent_comm_core.models.auth import Agent, User
from communication_server.websocket.auth import WebSocketAuth, get_token_from_query
from communication_server.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class StatusWebSocketHandler:
    """
    WebSocket handler for status board real-time updates.

    Manages WebSocket connections for status subscribers and
    broadcasts events for agent status changes, communications,
    and meeting events.
    """

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the status WebSocket handler.

        Args:
            connection_manager: Connection manager for WebSocket connections
        """
        self._connection_manager = connection_manager
        self._status_subscribers: set[WebSocket] = set()
        # Track authentication for subscribers
        self._subscriber_auth: dict[WebSocket, User | Agent] = {}

    async def handle_connection(self, websocket: WebSocket, token: str | None = None) -> None:
        """
        Handle a WebSocket connection for status updates.

        Args:
            websocket: WebSocket connection
            token: Authentication token (optional if already provided via query)
        """
        # Extract token from query if not provided
        if not token:
            token = get_token_from_query(websocket)

        # Authenticate connection
        auth = None
        if token:
            try:
                websocket, auth = await WebSocketAuth.authenticate_websocket(
                    websocket,
                    token,
                )
            except WebSocketDisconnect:
                # Connection already closed by authenticate_websocket
                return

        await websocket.accept()
        self._status_subscribers.add(websocket)
        if auth:
            self._subscriber_auth[websocket] = auth

        # Get participant name for logging
        participant_name = self._get_participant_name(auth) if auth else "Guest"

        try:
            # Send initial connection confirmation
            await websocket.send_json(
                {
                    "type": "connected",
                    "message": f"Status board WebSocket connected as {participant_name}",
                    "participant": participant_name,
                    "timestamp": _get_timestamp(),
                }
            )

            # Listen for incoming messages (keep-alive, subscribe/unsubscribe)
            while True:
                data = await websocket.receive_text()
                await self._handle_client_message(websocket, data, auth)

        except WebSocketDisconnect:
            logger.info(f"Status board WebSocket disconnected: {participant_name}")
        except Exception as e:
            logger.error(f"Error in status WebSocket: {e}")
        finally:
            self._status_subscribers.discard(websocket)
            self._subscriber_auth.pop(websocket, None)

    def _get_participant_name(self, auth: User | Agent | None) -> str:
        """
        Get display name for authenticated participant.

        Args:
            auth: User or Agent object (optional)

        Returns:
            Display name string
        """
        if isinstance(auth, User):
            return f"@{auth.username}"
        elif isinstance(auth, Agent):
            return f"@{auth.nickname}"
        else:
            return "Guest"

    async def _handle_client_message(
        self, websocket: WebSocket, message: str, auth: User | Agent | None
    ) -> None:
        """
        Handle a message from a connected client.

        Args:
            websocket: WebSocket connection
            message: JSON message from client
            auth: Authenticated user or agent (optional)
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": _get_timestamp()})
            elif msg_type == "subscribe":
                # Client wants specific events (can be extended)
                participant_name = self._get_participant_name(auth)
                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "filters": data.get("filters", {}),
                        "participant": participant_name,
                        "timestamp": _get_timestamp(),
                    }
                )
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message}")

    async def broadcast_agent_status_change(
        self, agent_id: str, old_status: str, new_status: str
    ) -> None:
        """
        Broadcast agent status change to all subscribers.

        Args:
            agent_id: Display agent ID
            old_status: Previous status
            new_status: New status
        """
        message = {
            "type": "agent_status_change",
            "data": {
                "agent_id": agent_id,
                "old_status": old_status,
                "new_status": new_status,
            },
            "timestamp": _get_timestamp(),
        }
        await self._broadcast_to_all(message)

    async def broadcast_new_communication(
        self, from_agent: str, to_agent: str, message_type: str
    ) -> None:
        """
        Broadcast new communication event.

        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID
            message_type: Type of message
        """
        message = {
            "type": "new_communication",
            "data": {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
            },
            "timestamp": _get_timestamp(),
        }
        await self._broadcast_to_all(message)

    async def broadcast_meeting_event(self, meeting_id: str, event_type: str, data: dict) -> None:
        """
        Broadcast meeting-related event.

        Args:
            meeting_id: Meeting ID
            event_type: Event type (started, ended, decision_made)
            data: Additional event data
        """
        message = {
            "type": "meeting_event",
            "data": {"meeting_id": meeting_id, "event_type": event_type, **data},
            "timestamp": _get_timestamp(),
        }
        await self._broadcast_to_all(message)

    async def broadcast_agent_registered(self, agent_id: str, nickname: str) -> None:
        """
        Broadcast new agent registration.

        Args:
            agent_id: Display agent ID
            nickname: Agent nickname
        """
        message = {
            "type": "agent_registered",
            "data": {"agent_id": agent_id, "nickname": nickname},
            "timestamp": _get_timestamp(),
        }
        await self._broadcast_to_all(message)

    async def broadcast_agent_unregistered(self, agent_id: str) -> None:
        """
        Broadcast agent unregistration.

        Args:
            agent_id: Display agent ID
        """
        message = {
            "type": "agent_unregistered",
            "data": {"agent_id": agent_id},
            "timestamp": _get_timestamp(),
        }
        await self._broadcast_to_all(message)

    async def _broadcast_to_all(self, message: dict) -> None:
        """
        Broadcast a message to all connected subscribers.

        Args:
            message: Message to broadcast
        """
        disconnected = set()

        for websocket in self._status_subscribers:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self._status_subscribers.discard(websocket)

    def get_subscriber_count(self) -> int:
        """
        Get the number of active subscribers.

        Returns:
            Number of connected WebSocket clients
        """
        return len(self._status_subscribers)


def _get_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO format timestamp string
    """
    from datetime import datetime

    return datetime.utcnow().isoformat()


# Global handler instance
_status_handler: StatusWebSocketHandler | None = None


def get_status_handler(connection_manager: ConnectionManager) -> StatusWebSocketHandler:
    """
    Get or create the status WebSocket handler.

    Args:
        connection_manager: Connection manager for WebSocket connections

    Returns:
        The StatusWebSocketHandler instance
    """
    global _status_handler
    if _status_handler is None:
        _status_handler = StatusWebSocketHandler(connection_manager)
    return _status_handler
