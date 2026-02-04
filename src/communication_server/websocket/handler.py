"""
WebSocket message handler for meeting communications.

Enhanced with comprehensive event broadcasting and reconnection handling.
"""

import json
import logging
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from agent_comm_core.models.auth import Agent, User
from agent_comm_core.services.discussion import DiscussionState
from communication_server.websocket.auth import WebSocketAuth, get_token_from_query
from communication_server.websocket.manager import ConnectionManager

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

    # Enhanced event types
    AGENT_JOINED = "agent_joined"
    OPINION_PRESENTED = "opinion_presented"
    CONSENSUS_REACHED = "consensus_reached"
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    DISCUSSION_PAUSED = "discussion_paused"
    DISCUSSION_RESUMED = "discussion_resumed"
    RECONNECT = "reconnect"
    STATE_SYNC = "state_sync"


@dataclass
class MeetingEvent:
    """A meeting event to broadcast."""

    event_type: MessageType
    meeting_id: UUID
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_id: str | None = None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert event to dictionary for WebSocket transmission."""
        return {
            "type": self.event_type.value,
            "meeting_id": str(self.meeting_id),
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "data": self.data,
        }


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
        token: str | None = None,
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
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Send error message for invalid JSON or format
            with suppress(OSError):
                await self._manager.send_personal_message(
                    {
                        "type": MessageType.ERROR,
                        "message": f"Invalid message format: {str(e)}",
                    },
                    websocket,
                )
            self._manager.disconnect(websocket)

    def _get_participant_name(self, auth: User | Agent) -> str:
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
        self, websocket: WebSocket, meeting_id: UUID, auth: User | Agent, data: dict
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
        except ValueError as err:
            raise ValueError(f"Unknown message type: {message_type}") from err

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

    async def _handle_opinion_request(
        self, websocket: WebSocket, meeting_id: UUID, auth: User | Agent, data: dict
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
        self, websocket: WebSocket, meeting_id: UUID, auth: User | Agent, data: dict
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
        self, websocket: WebSocket, meeting_id: UUID, auth: User | Agent, data: dict
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
        self, websocket: WebSocket, meeting_id: UUID, auth: User | Agent, data: dict
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

    # ========================================================================
    # Enhanced Event Broadcasting Methods
    # ========================================================================

    async def broadcast_agent_joined(
        self, meeting_id: UUID, agent_id: str, participant_name: str
    ) -> None:
        """
        Broadcast an agent_joined event to all participants.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent who joined
            participant_name: Display name of the agent
        """
        event = MeetingEvent(
            event_type=MessageType.AGENT_JOINED,
            meeting_id=meeting_id,
            agent_id=agent_id,
            data={"participant_name": participant_name},
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    async def broadcast_opinion_presented(
        self, meeting_id: UUID, agent_id: str, opinion: str, round_number: int = 1
    ) -> None:
        """
        Broadcast an opinion_presented event to all participants.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent presenting opinion
            opinion: The opinion content
            round_number: Current discussion round
        """
        event = MeetingEvent(
            event_type=MessageType.OPINION_PRESENTED,
            meeting_id=meeting_id,
            agent_id=agent_id,
            data={
                "opinion": opinion,
                "round_number": round_number,
            },
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    async def broadcast_consensus_reached(
        self, meeting_id: UUID, consensus_option: str, votes: dict[str, str]
    ) -> None:
        """
        Broadcast a consensus_reached event to all participants.

        Args:
            meeting_id: Meeting ID
            consensus_option: The option that reached consensus
            votes: Dictionary of all votes
        """
        event = MeetingEvent(
            event_type=MessageType.CONSENSUS_REACHED,
            meeting_id=meeting_id,
            data={
                "consensus_option": consensus_option,
                "votes": votes,
            },
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    async def broadcast_round_started(
        self, meeting_id: UUID, round_number: int, topic: str
    ) -> None:
        """
        Broadcast a round_started event to all participants.

        Args:
            meeting_id: Meeting ID
            round_number: Round number
            topic: Discussion topic for the round
        """
        event = MeetingEvent(
            event_type=MessageType.ROUND_STARTED,
            meeting_id=meeting_id,
            data={
                "round_number": round_number,
                "topic": topic,
            },
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    async def broadcast_round_completed(
        self,
        meeting_id: UUID,
        round_number: int,
        consensus_reached: bool,
        consensus_option: str | None = None,
    ) -> None:
        """
        Broadcast a round_completed event to all participants.

        Args:
            meeting_id: Meeting ID
            round_number: Round number
            consensus_reached: Whether consensus was reached
            consensus_option: The consensus option if reached
        """
        event = MeetingEvent(
            event_type=MessageType.ROUND_COMPLETED,
            meeting_id=meeting_id,
            data={
                "round_number": round_number,
                "consensus_reached": consensus_reached,
                "consensus_option": consensus_option,
            },
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    async def broadcast_discussion_paused(self, meeting_id: UUID, reason: str) -> None:
        """
        Broadcast a discussion_paused event to all participants.

        Args:
            meeting_id: Meeting ID
            reason: Reason for pausing
        """
        event = MeetingEvent(
            event_type=MessageType.DISCUSSION_PAUSED,
            meeting_id=meeting_id,
            data={"reason": reason},
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    async def broadcast_discussion_resumed(self, meeting_id: UUID) -> None:
        """
        Broadcast a discussion_resumed event to all participants.

        Args:
            meeting_id: Meeting ID
        """
        event = MeetingEvent(
            event_type=MessageType.DISCUSSION_RESUMED,
            meeting_id=meeting_id,
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())

    # ========================================================================
    # Reconnection Handling
    # ========================================================================

    async def handle_reconnect(
        self, websocket: WebSocket, meeting_id: UUID, agent_id: str, last_sequence: int = 0
    ) -> bool:
        """
        Handle a reconnection attempt from an agent.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            agent_id: Agent attempting to reconnect
            last_sequence: Last message sequence number the agent received

        Returns:
            True if reconnection successful, False otherwise
        """
        # Check if meeting exists and is active
        participants = self._manager.get_participants(meeting_id)
        if not participants:
            logger.warning(f"Reconnection failed: no participants for meeting {meeting_id}")
            return False

        # Log reconnection for monitoring
        logger.info(
            f"Agent {agent_id} reconnecting to meeting {meeting_id} from sequence {last_sequence}"
        )

        # Send state sync with recent messages
        await self._send_state_sync(websocket, meeting_id, last_sequence)

        return True

    async def _send_state_sync(
        self, websocket: WebSocket, meeting_id: UUID, since_sequence: int
    ) -> None:
        """
        Send state synchronization message to a reconnecting client.

        Args:
            websocket: WebSocket connection
            meeting_id: Meeting ID
            since_sequence: Only send messages after this sequence
        """
        # Get current state
        participants = self._manager.get_participants(meeting_id)
        participant_names = [self._get_participant_name(p) for p in participants]

        # Create state sync message
        state_sync = {
            "type": MessageType.STATE_SYNC.value,
            "meeting_id": str(meeting_id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "current_participants": participant_names,
                "connection_count": self._manager.get_connection_count(meeting_id),
                "last_sequence": since_sequence,
            },
        }

        await self._manager.send_personal_message(state_sync, websocket)

    async def broadcast_meeting_state(
        self, meeting_id: UUID, discussion_state: DiscussionState
    ) -> None:
        """
        Broadcast full meeting state to all participants.

        Args:
            meeting_id: Meeting ID
            discussion_state: Current discussion state
        """
        state_data = {
            "current_round": discussion_state.current_round,
            "max_rounds": discussion_state.max_rounds,
            "current_speaker": discussion_state.current_speaker,
            "participant_count": len(discussion_state.participants),
            "consensus_threshold": discussion_state.consensus_threshold,
        }

        event = MeetingEvent(
            event_type=MessageType.STATE_SYNC,
            meeting_id=meeting_id,
            data=state_data,
        )
        await self._manager.broadcast_to_meeting(meeting_id, event.to_dict())
