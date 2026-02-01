"""
WebSocket connection manager for meeting participants.

Manages active WebSocket connections per meeting and provides
broadcast functionality for real-time communication.
"""

from collections import defaultdict
from typing import Dict, Set, Union, Optional
from uuid import UUID

from fastapi import WebSocket

from agent_comm_core.models.auth import Agent, User


class ConnectionManager:
    """
    Manager for WebSocket connections.

    Tracks active connections per meeting and provides methods
    for broadcasting messages to all participants.
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        # Map meeting_id -> set of active connections
        self._meeting_connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        # Map connection -> meeting_id
        self._connection_meetings: Dict[WebSocket, UUID] = {}
        # Map connection -> authenticated user or agent
        self._connection_auth: Dict[WebSocket, Union[User, Agent]] = {}
        # Map meeting_id -> set of authenticated users/agents
        self._meeting_participants: Dict[UUID, Set[Union[User, Agent]]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        meeting_id: UUID,
        auth: Optional[Union[User, Agent]] = None,
    ) -> None:
        """
        Connect a WebSocket to a meeting.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID to connect to
            auth: Authenticated user or agent (optional)
        """
        await websocket.accept()
        self._meeting_connections[meeting_id].add(websocket)
        self._connection_meetings[websocket] = meeting_id
        if auth:
            self._connection_auth[websocket] = auth
            self._meeting_participants[meeting_id].add(auth)

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket from its meeting.

        Args:
            websocket: WebSocket connection
        """
        meeting_id = self._connection_meetings.pop(websocket, None)
        if meeting_id:
            self._meeting_connections[meeting_id].discard(websocket)
            # Remove auth info
            auth = self._connection_auth.pop(websocket, None)
            if auth:
                self._meeting_participants[meeting_id].discard(auth)
            # Clean up empty meeting
            if not self._meeting_connections[meeting_id]:
                del self._meeting_connections[meeting_id]
                self._meeting_participants.pop(meeting_id, None)

    def get_auth(self, websocket: WebSocket) -> Optional[Union[User, Agent]]:
        """
        Get authenticated user or agent for a connection.

        Args:
            websocket: WebSocket connection

        Returns:
            User or Agent object if authenticated, None otherwise
        """
        return self._connection_auth.get(websocket)

    def get_participants(self, meeting_id: UUID) -> Set[Union[User, Agent]]:
        """
        Get all authenticated participants for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            Set of User and Agent objects
        """
        return self._meeting_participants.get(meeting_id, set()).copy()

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """
        Send a message to a specific connection.

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception:
            # Connection may be closed
            self.disconnect(websocket)

    async def broadcast_to_meeting(self, meeting_id: UUID, message: dict) -> None:
        """
        Broadcast a message to all connections in a meeting.

        Args:
            meeting_id: Meeting ID
            message: Message dictionary to broadcast
        """
        connections = self._meeting_connections.get(meeting_id, set()).copy()
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Remove failed connection
                self.disconnect(connection)

    async def broadcast_to_meeting_excluding(
        self, meeting_id: UUID, message: dict, exclude: WebSocket
    ) -> None:
        """
        Broadcast a message to all connections except one.

        Args:
            meeting_id: Meeting ID
            message: Message dictionary to broadcast
            exclude: WebSocket to exclude from broadcast
        """
        connections = self._meeting_connections.get(meeting_id, set()).copy()
        for connection in connections:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Remove failed connection
                    self.disconnect(connection)

    def get_connection_count(self, meeting_id: UUID) -> int:
        """
        Get the number of active connections for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            Number of active connections
        """
        return len(self._meeting_connections.get(meeting_id, set()))

    def get_meeting_for_connection(self, websocket: WebSocket) -> UUID | None:
        """
        Get the meeting ID for a connection.

        Args:
            websocket: WebSocket connection

        Returns:
            Meeting ID or None if not connected
        """
        return self._connection_meetings.get(websocket)

    def is_connection_active(self, websocket: WebSocket) -> bool:
        """
        Check if a connection is still active.

        Args:
            websocket: WebSocket connection

        Returns:
            True if connection is active, False otherwise
        """
        return websocket in self._connection_meetings
