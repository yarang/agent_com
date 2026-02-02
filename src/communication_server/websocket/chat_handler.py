"""
WebSocket handler for chat room connections.

Handles WebSocket connections for real-time chat messaging.
"""

from uuid import UUID

from fastapi import WebSocket, status

from agent_comm_core.models.auth import Agent, User
from communication_server.websocket.chat_manager import ChatConnectionManager


class ChatWebSocketHandler:
    """
    Handler for chat room WebSocket connections.

    Manages individual WebSocket connections and handles incoming messages.
    """

    def __init__(self, manager: ChatConnectionManager) -> None:
        """
        Initialize the handler with a connection manager.

        Args:
            manager: Chat connection manager
        """
        self.manager = manager

    async def handle_connection(
        self,
        websocket: WebSocket,
        room_id: UUID,
        token: str | None = None,
    ) -> None:
        """
        Handle a WebSocket connection for a chat room.

        Args:
            websocket: WebSocket connection
            room_id: Chat room ID
            token: Authentication token (optional for development)
        """
        # Authenticate connection
        auth = await self._authenticate_connection(websocket, room_id, token)
        if auth is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect to room
        await self.manager.connect(websocket, room_id, auth)

        # Send welcome message
        await self.manager.send_personal_message(
            {
                "event": "chat.connected",
                "room_id": str(room_id),
                "data": {
                    "message": "Connected to chat room",
                    "connection_count": self.manager.get_connection_count(room_id),
                },
            },
            websocket,
        )

        try:
            # Handle incoming messages
            while True:
                data = await websocket.receive_json()
                await self._handle_message(websocket, room_id, auth, data)

        except Exception:
            # Connection closed
            pass
        finally:
            self.manager.disconnect(websocket)

    async def _authenticate_connection(
        self,
        websocket: WebSocket,
        room_id: UUID,
        token: str | None = None,
    ) -> User | Agent | None:
        """
        Authenticate a WebSocket connection.

        Args:
            websocket: WebSocket connection
            room_id: Chat room ID
            token: Authentication token

        Returns:
            Authenticated User or Agent, or None if authentication fails
        """
        # For development, allow connections without token
        # In production, implement proper JWT/API token validation
        if not token:
            return None

        try:
            from communication_server.security.auth import AuthService, get_auth_service

            auth_service: AuthService = get_auth_service()

            # Try to validate as JWT token (user)
            try:
                user = await auth_service.get_current_user(token)
                return user
            except Exception:
                pass

            # Try to validate as API token (agent)
            try:
                agent = await auth_service.get_current_agent(token)
                return agent
            except Exception:
                pass

        except Exception:
            pass

        return None

    async def _handle_message(
        self,
        websocket: WebSocket,
        room_id: UUID,
        auth: User | Agent,
        data: dict,
    ) -> None:
        """
        Handle an incoming WebSocket message.

        Args:
            websocket: WebSocket connection
            room_id: Chat room ID
            auth: Authenticated user or agent
            data: Message data
        """
        event = data.get("event")

        if event == "chat.typing":
            # Handle typing indicator
            is_typing = data.get("data", {}).get("is_typing", False)
            sender_type = "user" if isinstance(auth, User) else "agent"
            await self.manager.broadcast_typing(
                room_id=room_id,
                sender_id=auth.id,
                sender_type=sender_type,
                is_typing=is_typing,
            )

        elif event == "chat.message":
            # Handle direct WebSocket message (alternative to REST API)
            await self._handle_chat_message(websocket, room_id, auth, data)

        else:
            # Unknown event
            await self.manager.send_personal_message(
                {
                    "event": "error",
                    "data": {
                        "message": f"Unknown event: {event}",
                    },
                },
                websocket,
            )

    async def _handle_chat_message(
        self,
        websocket: WebSocket,
        room_id: UUID,
        auth: User | Agent,
        data: dict,
    ) -> None:
        """
        Handle a chat message sent via WebSocket.

        Args:
            websocket: WebSocket connection
            room_id: Chat room ID
            auth: Authenticated user or agent
            data: Message data
        """
        from agent_comm_core.db.database import db_session
        from agent_comm_core.db.models.chat import SenderType
        from agent_comm_core.repositories import ChatRepository

        message_data = data.get("data", {})
        content = message_data.get("content", "")
        message_type = message_data.get("message_type", "text")
        metadata = message_data.get("metadata")

        if not content:
            await self.manager.send_personal_message(
                {
                    "event": "error",
                    "data": {
                        "message": "Message content is required",
                    },
                },
                websocket,
            )
            return

        # Verify participant access
        async with db_session() as session:
            repo = ChatRepository(session)

            sender_type = SenderType.USER if isinstance(auth, User) else SenderType.AGENT
            is_participant = await repo.is_participant(
                room_id,
                user_id=auth.id if isinstance(auth, User) else None,
                agent_id=auth.id if isinstance(auth, Agent) else None,
            )

            if not is_participant:
                await self.manager.send_personal_message(
                    {
                        "event": "error",
                        "data": {
                            "message": "Not a participant in this room",
                        },
                    },
                    websocket,
                )
                return

            # Create message
            message = await repo.create_message(
                room_id=room_id,
                sender_type=sender_type,
                sender_id=auth.id,
                content=content,
                message_type=message_type,
                metadata=metadata,
            )

            await session.commit()
            await session.refresh(message)

            # Broadcast to all participants
            await self.manager.broadcast_message(
                room_id=room_id,
                message_id=message.id,
                sender_type=sender_type.value,
                sender_id=auth.id,
                content=content,
                message_type=message_type,
                metadata=metadata,
            )
