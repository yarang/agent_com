"""
WebSocket message handler for meeting communications.

Handles incoming WebSocket messages and routes them to
appropriate handlers based on message type.
"""

from enum import Enum
from typing import Optional, Union
from uuid import UUID
import logging

from fastapi import WebSocket, WebSocketDisconnect

from agent_comm_core.models.auth import Agent, User

from communication_server.websocket.manager import ConnectionManager
from communication_server.websocket.auth import WebSocketAuth, get_token_from_query

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""

    # Request types
    OPINION_REQUEST = "opinion_request"
    CONSENSUS_REQUEST = "consensus_request"

    # Response types
    OPINION = "opinion"
    CONSENSUS_VOTE = "consensus_vote"

    # Control types
    JOIN = "join"
    LEAVE = "leave"
    ERROR = "error"


class WebSocketHandler:
    """
    Handler for WebSocket messages.

    Processes incoming messages, validates their format,
    and takes appropriate action based on message type.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        """
        Initialize the handler.

        Args:
            manager: Connection manager instance
        """
        self._manager = manager

    async def handle_connection(
        self,
        websocket: WebSocket,
        meeting_id: UUID,
        token: Optional[str] = None,
    ) -> None:
        """
        Handle a WebSocket connection for a meeting.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            token: Authentication token (optional if already provided via query)
        """
        # Extract token from query if not provided
        if not token:
            token = get_token_from_query(websocket)

        # Authenticate connection
        try:
            websocket, auth = await WebSocketAuth.authenticate_websocket(
                websocket,
                token,
            )
        except WebSocketDisconnect:
            # Connection already closed by authenticate_websocket
            return

        # Connect with authenticated user/agent
        await self._manager.connect(websocket, meeting_id, auth)

        # Get participant info for welcome message
        participant_name = self._get_participant_name(auth)

        # Send welcome message
        await self._manager.send_personal_message(
            {
                "type": "join",
                "meeting_id": str(meeting_id),
                "message": f"Connected to meeting as {participant_name}",
                "participant": participant_name,
            },
            websocket,
        )

        try:
            while True:
                # Receive JSON message
                data = await websocket.receive_json()

                # Handle message based on type
                await self._handle_message(websocket, meeting_id, auth, data)

        except WebSocketDisconnect:
            self._manager.disconnect(websocket)
            # Notify others
            await self._manager.broadcast_to_meeting(
                meeting_id,
                {
                    "type": "leave",
                    "message": f"{participant_name} has left the meeting",
                    "participant": participant_name,
                },
            )
        except Exception as e:
            # Send error message
            try:
                await self._manager.send_personal_message(
                    {
                        "type": MessageType.ERROR,
                        "message": f"Error: {str(e)}",
                    },
                    websocket,
                )
            except Exception:
                pass
            self._manager.disconnect(websocket)

    def _get_participant_name(self, auth: Union[User, Agent]) -> str:
        """
        Get display name for authenticated participant.

        Args:
            auth: User or Agent object

        Returns:
            Display name string
        """
        if isinstance(auth, User):
            return f"@{auth.username}"
        elif isinstance(auth, Agent):
            return f"@{auth.nickname}"
        else:
            return "Anonymous"

    async def _handle_message(
        self, websocket: WebSocket, meeting_id: UUID, auth: Union[User, Agent], data: dict
    ) -> None:
        """
        Handle an incoming message.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            auth: Authenticated user or agent
            data: Message data

        Raises:
            ValueError: If message format is invalid
        """
        message_type = data.get("type")

        if not message_type:
            raise ValueError("Message missing 'type' field")

        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise ValueError(f"Unknown message type: {message_type}")

        if msg_type == MessageType.OPINION_REQUEST:
            await self._handle_opinion_request(websocket, meeting_id, auth, data)
        elif msg_type == MessageType.OPINION:
            await self._handle_opinion(websocket, meeting_id, auth, data)
        elif msg_type == MessageType.CONSENSUS_REQUEST:
            await self._handle_consensus_request(websocket, meeting_id, auth, data)
        elif msg_type == MessageType.CONSENSUS_VOTE:
            await self._handle_consensus_vote(websocket, meeting_id, auth, data)
        else:
            raise ValueError(f"Unhandled message type: {message_type}")
        """
        Handle an incoming message.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            data: Message data

        Raises:
            ValueError: If message format is invalid
        """
        message_type = data.get("type")

        if not message_type:
            raise ValueError("Message missing 'type' field")

        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise ValueError(f"Unknown message type: {message_type}")

        if msg_type == MessageType.OPINION_REQUEST:
            await self._handle_opinion_request(websocket, meeting_id, data)
        elif msg_type == MessageType.OPINION:
            await self._handle_opinion(websocket, meeting_id, data)
        elif msg_type == MessageType.CONSENSUS_REQUEST:
            await self._handle_consensus_request(websocket, meeting_id, data)
        elif msg_type == MessageType.CONSENSUS_VOTE:
            await self._handle_consensus_vote(websocket, meeting_id, data)
        else:
            raise ValueError(f"Unhandled message type: {message_type}")

    async def _handle_opinion_request(
        self, websocket: WebSocket, meeting_id: UUID, auth: Union[User, Agent], data: dict
    ) -> None:
        """
        Handle an opinion request message.

        Broadcasts the request to all other participants in the meeting.

        Args:
            websocket: WebSocket connection of the requester
            meeting_id: Meeting ID
            auth: Authenticated user or agent
            data: Message data containing agent_id, question, and context
        """
        # Use authenticated participant info
        agent_id = data.get("agent_id", self._get_participant_name(auth))
        question = data.get("question")

        if not question:
            await self._manager.send_personal_message(
                {
                    "type": MessageType.ERROR,
                    "message": "opinion_request must include question",
                },
                websocket,
            )
            return

        # Broadcast to other participants
        await self._manager.broadcast_to_meeting_excluding(
            meeting_id,
            {
                "type": MessageType.OPINION_REQUEST,
                "agent_id": agent_id,
                "question": question,
                "context": data.get("context", {}),
            },
            websocket,
        )

    async def _handle_opinion(
        self, websocket: WebSocket, meeting_id: UUID, auth: Union[User, Agent], data: dict
    ) -> None:
        """
        Handle an opinion message.

        Broadcasts the opinion to all participants in the meeting.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            auth: Authenticated user or agent
            data: Message data containing agent_id and opinion
        """
        # Use authenticated participant info
        agent_id = data.get("agent_id", self._get_participant_name(auth))
        opinion = data.get("opinion")

        if opinion is None:
            await self._manager.send_personal_message(
                {
                    "type": MessageType.ERROR,
                    "message": "opinion must include opinion",
                },
                websocket,
            )
            return

        # Broadcast to all participants
        await self._manager.broadcast_to_meeting(
            meeting_id,
            {
                "type": MessageType.OPINION,
                "agent_id": agent_id,
                "opinion": opinion,
                "in_reply_to": data.get("in_reply_to"),
            },
        )

    async def _handle_consensus_request(
        self, websocket: WebSocket, meeting_id: UUID, auth: Union[User, Agent], data: dict
    ) -> None:
        """
        Handle a consensus request message.

        Broadcasts the consensus request to all participants.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            auth: Authenticated user or agent
            data: Message data containing proposal details
        """
        proposal = data.get("proposal")
        options = data.get("options", [])

        if not proposal or not options:
            await self._manager.send_personal_message(
                {
                    "type": MessageType.ERROR,
                    "message": "consensus_request must include proposal and options",
                },
                websocket,
            )
            return

        # Broadcast to all participants
        await self._manager.broadcast_to_meeting(
            meeting_id,
            {
                "type": MessageType.CONSENSUS_REQUEST,
                "proposal": proposal,
                "options": options,
                "deadline": data.get("deadline"),
                "requested_by": self._get_participant_name(auth),
            },
        )

    async def _handle_consensus_vote(
        self, websocket: WebSocket, meeting_id: UUID, auth: Union[User, Agent], data: dict
    ) -> None:
        """
        Handle a consensus vote message.

        Broadcasts the vote to all participants.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            auth: Authenticated user or agent
            data: Message data containing agent_id and vote
        """
        # Use authenticated participant info
        agent_id = data.get("agent_id", self._get_participant_name(auth))
        vote = data.get("vote")

        if vote is None:
            await self._manager.send_personal_message(
                {
                    "type": MessageType.ERROR,
                    "message": "consensus_vote must include vote",
                },
                websocket,
            )
            return

        # Broadcast to all participants
        await self._manager.broadcast_to_meeting(
            meeting_id,
            {
                "type": MessageType.CONSENSUS_VOTE,
                "agent_id": agent_id,
                "vote": vote,
                "rationale": data.get("rationale", ""),
            },
        )
