"""
WebSocket connection manager for chat rooms.

Manages active WebSocket connections for chat rooms and provides
broadcast functionality for real-time messaging.
"""

from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

from agent_comm_core.models.auth import Agent, User


class ChatConnectionManager:
    """
    Manager for WebSocket connections in chat rooms.

    Tracks active connections per room and provides methods
    for broadcasting messages to all participants.
    """

    def __init__(self) -> None:
        """Initialize the chat connection manager."""
        # Map room_id -> set of active connections
        self._room_connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        # Map connection -> room_id
        self._connection_rooms: dict[WebSocket, UUID] = {}
        # Map connection -> authenticated user or agent
        self._connection_auth: dict[WebSocket, User | Agent] = {}
        # Map room_id -> set of authenticated users/agents
        self._room_participants: dict[UUID, set[User | Agent]] = defaultdict(set)
        # Map room_id -> typing indicators {sender_id: is_typing}
        self._typing_indicators: dict[UUID, dict[UUID, bool]] = defaultdict(dict)

    async def connect(
        self,
        websocket: WebSocket,
        room_id: UUID,
        auth: User | Agent | None = None,
    ) -> None:
        """
        Connect a WebSocket to a chat room.

        Args:
            websocket: WebSocket connection
            room_id: Chat room ID to connect to
            auth: Authenticated user or agent (optional)
        """
        await websocket.accept()
        self._room_connections[room_id].add(websocket)
        self._connection_rooms[websocket] = room_id
        if auth:
            self._connection_auth[websocket] = auth
            self._room_participants[room_id].add(auth)

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket from its chat room.

        Args:
            websocket: WebSocket connection
        """
        room_id = self._connection_rooms.pop(websocket, None)
        if room_id:
            self._room_connections[room_id].discard(websocket)
            # Remove auth info
            auth = self._connection_auth.pop(websocket, None)
            if auth:
                self._room_participants[room_id].discard(auth)
            # Clean up empty room
            if not self._room_connections[room_id]:
                del self._room_connections[room_id]
                self._room_participants.pop(room_id, None)
                self._typing_indicators.pop(room_id, None)

    def get_auth(self, websocket: WebSocket) -> User | Agent | None:
        """
        Get authenticated user or agent for a connection.

        Args:
            websocket: WebSocket connection

        Returns:
            User or Agent object if authenticated, None otherwise
        """
        return self._connection_auth.get(websocket)

    def get_participants(self, room_id: UUID) -> set[User | Agent]:
        """
        Get all authenticated participants for a room.

        Args:
            room_id: Room ID

        Returns:
            Set of User and Agent objects
        """
        return self._room_participants.get(room_id, set()).copy()

    async def broadcast_message(
        self,
        room_id: UUID,
        message_id: UUID,
        sender_type: str,
        sender_id: UUID,
        content: str,
        message_type: str = "text",
        metadata: dict | None = None,
    ) -> None:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: Room ID
            message_id: Message UUID
            sender_type: Sender type (user or agent)
            sender_id: Sender UUID
            content: Message content
            message_type: Message type
            metadata: Optional metadata
        """
        message_data = {
            "event": "chat.message",
            "room_id": str(room_id),
            "data": {
                "id": str(message_id),
                "sender_type": sender_type,
                "sender_id": str(sender_id),
                "content": content,
                "message_type": message_type,
                "metadata": metadata,
            },
        }
        await self._broadcast_to_room(room_id, message_data)

    async def broadcast_participant_joined(
        self,
        room_id: UUID,
        participant_id: UUID,
        participant_type: str,
    ) -> None:
        """
        Broadcast participant joined event.

        Args:
            room_id: Room ID
            participant_id: Participant UUID
            participant_type: Participant type (user or agent)
        """
        message_data = {
            "event": "chat.participant_joined",
            "room_id": str(room_id),
            "data": {
                "id": str(participant_id),
                "type": participant_type,
            },
        }
        await self._broadcast_to_room(room_id, message_data)

    async def broadcast_participant_left(
        self,
        room_id: UUID,
        participant_id: UUID,
        participant_type: str,
    ) -> None:
        """
        Broadcast participant left event.

        Args:
            room_id: Room ID
            participant_id: Participant UUID
            participant_type: Participant type (user or agent)
        """
        message_data = {
            "event": "chat.participant_left",
            "room_id": str(room_id),
            "data": {
                "id": str(participant_id),
                "type": participant_type,
            },
        }
        await self._broadcast_to_room(room_id, message_data)

    async def broadcast_typing(
        self,
        room_id: UUID,
        sender_id: UUID,
        sender_type: str,
        is_typing: bool,
    ) -> None:
        """
        Broadcast typing indicator to room.

        Args:
            room_id: Room ID
            sender_id: Sender UUID
            sender_type: Sender type (user or agent)
            is_typing: Whether currently typing
        """
        # Update typing state
        self._typing_indicators[room_id][sender_id] = is_typing

        message_data = {
            "event": "chat.typing",
            "room_id": str(room_id),
            "data": {
                "sender_id": str(sender_id),
                "sender_type": sender_type,
                "is_typing": is_typing,
            },
        }
        await self._broadcast_to_room(room_id, message_data)

    def get_typing_indicators(self, room_id: UUID) -> dict[UUID, bool]:
        """
        Get active typing indicators for a room.

        Args:
            room_id: Room ID

        Returns:
            Dictionary mapping sender_id to is_typing
        """
        return self._typing_indicators.get(room_id, {}).copy()

    async def _broadcast_to_room(self, room_id: UUID, message: dict) -> None:
        """
        Internal method to broadcast to all connections in a room.

        Args:
            room_id: Room ID
            message: Message dictionary to broadcast
        """
        connections = self._room_connections.get(room_id, set()).copy()
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Remove failed connection
                self.disconnect(connection)

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

    def get_connection_count(self, room_id: UUID) -> int:
        """
        Get the number of active connections for a room.

        Args:
            room_id: Room ID

        Returns:
            Number of active connections
        """
        return len(self._room_connections.get(room_id, set()))

    def get_room_for_connection(self, websocket: WebSocket) -> UUID | None:
        """
        Get the room ID for a connection.

        Args:
            websocket: WebSocket connection

        Returns:
            Room ID or None if not connected
        """
        return self._connection_rooms.get(websocket)

    def is_connection_active(self, websocket: WebSocket) -> bool:
        """
        Check if a connection is still active.

        Args:
            websocket: WebSocket connection

        Returns:
            True if connection is active, False otherwise
        """
        return websocket in self._connection_rooms


# Global singleton instance
_chat_manager: ChatConnectionManager | None = None


def get_chat_manager() -> ChatConnectionManager:
    """
    Get the global chat connection manager instance.

    Returns:
        ChatConnectionManager instance
    """
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = ChatConnectionManager()
    return _chat_manager
