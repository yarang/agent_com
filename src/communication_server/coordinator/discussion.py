"""
Sequential discussion coordinator for agent meetings.

Orchestrates round-robin discussions where agents speak in order,
share opinions, and reach consensus on decisions.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from agent_comm_core.models.meeting import Meeting, MeetingStatus
from agent_comm_core.repositories.base import MeetingRepository
from agent_comm_core.services.discussion import DiscussionService

from communication_server.websocket.manager import ConnectionManager


class DiscussionPhase(str, Enum):
    """Phase of a sequential discussion."""

    INITIALIZING = "initializing"
    OPINION_COLLECTION = "opinion_collection"
    CONSENSUS_BUILDING = "consensus_building"
    DECISION = "decision"
    NO_CONSENSUS = "no_consensus"
    COMPLETED = "completed"


@dataclass
class SpeakerState:
    """State of a speaker in the discussion."""

    agent_id: str
    has_spoken: bool = False
    opinion: Optional[str] = None
    vote: Optional[str] = None


@dataclass
class DiscussionCoordinatorState:
    """State of a discussion coordinator."""

    meeting_id: UUID
    phase: DiscussionPhase = DiscussionPhase.INITIALIZING
    speakers: deque[str] = field(default_factory=deque)
    speaker_states: dict[str, SpeakerState] = field(default_factory=dict)
    current_speaker: Optional[str] = None
    current_question: Optional[str] = None
    opinions: dict[str, str] = field(default_factory=dict)
    votes: dict[str, str] = field(default_factory=dict)
    consensus_threshold: float = 0.75
    started_at: Optional[datetime] = None
    timeout_seconds: int = 300


class DiscussionCoordinator:
    """
    Coordinator for sequential agent discussions.

    Manages the flow of discussion including:
    - Determining speaking order
    - Requesting opinions via WebSocket
    - Collecting responses with timeout
    - Facilitating consensus phase
    - Recording decisions
    """

    def __init__(
        self,
        meeting_id: UUID,
        repository: MeetingRepository,
        ws_manager: ConnectionManager,
        discussion_service: DiscussionService,
        timeout_seconds: int = 300,
    ) -> None:
        """
        Initialize the coordinator.

        Args:
            meeting_id: Meeting ID
            repository: Meeting repository instance
            ws_manager: WebSocket connection manager
            discussion_service: Discussion service instance
            timeout_seconds: Timeout for each phase (default: 300 seconds)
        """
        self._meeting_id = meeting_id
        self._repository = repository
        self._ws_manager = ws_manager
        self._discussion_service = discussion_service
        self._state = DiscussionCoordinatorState(
            meeting_id=meeting_id,
            timeout_seconds=timeout_seconds,
        )
        self._running = False

    async def start(self, initial_question: Optional[str] = None) -> Meeting:
        """
        Start the discussion coordinator.

        Args:
            initial_question: Optional initial question for the discussion

        Returns:
            The started meeting

        Raises:
            ValueError: If meeting not found or no participants
        """
        # Get meeting and participants
        meeting = await self._repository.get_by_id(self._meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {self._meeting_id} not found")

        participants = await self._repository.get_participants(self._meeting_id)
        if not participants:
            raise ValueError(f"Meeting {self._meeting_id} has no participants")

        # Initialize speaker order
        participant_ids = deque(p.agent_id for p in participants)
        self._state.speakers = participant_ids
        self._state.speaker_states = {
            agent_id: SpeakerState(agent_id=agent_id) for agent_id in participant_ids
        }
        self._state.current_speaker = participant_ids[0] if participant_ids else None
        self._state.current_question = initial_question
        self._state.started_at = datetime.utcnow()
        self._state.phase = DiscussionPhase.OPINION_COLLECTION

        # Update meeting status
        await self._repository.update_status(self._meeting_id, MeetingStatus.ACTIVE)

        # Start the discussion via DiscussionService
        await self._discussion_service.start_discussion(
            self._meeting_id,
            initial_speaker_id=self._state.current_speaker,
        )

        return meeting

    async def request_opinions(
        self, question: str, context: Optional[dict] = None
    ) -> dict[str, str]:
        """
        Request opinions from all participants sequentially.

        Args:
            question: Question to ask all participants
            context: Optional context for the question

        Returns:
            Dictionary mapping agent IDs to their opinions

        Raises:
            ValueError: If discussion is not active
        """
        if self._state.phase != DiscussionPhase.OPINION_COLLECTION:
            raise ValueError(f"Cannot request opinions in phase {self._state.phase}")

        self._state.current_question = question
        self._state.opinions = {}

        # Request opinions from each speaker in order
        for agent_id in list(self._state.speakers):
            self._state.current_speaker = agent_id

            # Send opinion request via WebSocket
            await self._ws_manager.broadcast_to_meeting(
                self._meeting_id,
                {
                    "type": "opinion_request",
                    "agent_id": agent_id,
                    "question": question,
                    "context": context or {},
                },
            )

            # Wait for response with timeout
            try:
                opinion = await asyncio.wait_for(
                    self._wait_for_opinion(agent_id),
                    timeout=self._state.timeout_seconds,
                )
                self._state.opinions[agent_id] = opinion

                # Record opinion in discussion service
                await self._discussion_service.record_opinion(
                    self._meeting_id,
                    agent_id,
                    opinion,
                )

            except asyncio.TimeoutError:
                # Mark as no response
                self._state.opinions[agent_id] = "[NO RESPONSE]"

        return self._state.opinions.copy()

    async def _wait_for_opinion(self, agent_id: str) -> str:
        """
        Wait for an opinion from a specific agent.

        This method would normally integrate with a message queue
        or event system. For now, it's a placeholder.

        Args:
            agent_id: Agent to wait for

        Returns:
            The opinion provided by the agent
        """
        # In a real implementation, this would wait for a WebSocket message
        # or a callback. For now, we'll use a simple future-based approach.
        future = asyncio.Future()

        # This would be set by the WebSocket handler when receiving an opinion
        # For now, we'll return a placeholder
        return await future

    async def facilitate_consensus(
        self,
        proposal: str,
        options: list[str],
        deadline: Optional[datetime] = None,
    ) -> dict[str, str]:
        """
        Facilitate a consensus voting phase.

        Args:
            proposal: The proposal to vote on
            options: List of options to vote for
            deadline: Optional deadline for the vote

        Returns:
            Dictionary mapping agent IDs to their votes

        Raises:
            ValueError: If opinions haven't been collected yet
        """
        if not self._state.opinions:
            raise ValueError("Must collect opinions before facilitating consensus")

        self._state.phase = DiscussionPhase.CONSENSUS_BUILDING
        self._state.votes = {}

        # Request votes from all participants
        await self._ws_manager.broadcast_to_meeting(
            self._meeting_id,
            {
                "type": "consensus_request",
                "proposal": proposal,
                "options": options,
                "deadline": deadline.isoformat() if deadline else None,
            },
        )

        # Wait for votes with timeout
        deadline_time = deadline or (
            datetime.utcnow() + timedelta(seconds=self._state.timeout_seconds)
        )

        for agent_id in list(self._state.speakers):
            try:
                time_remaining = (deadline_time - datetime.utcnow()).total_seconds()
                if time_remaining <= 0:
                    break

                vote = await asyncio.wait_for(
                    self._wait_for_vote(agent_id),
                    timeout=min(time_remaining, self._state.timeout_seconds),
                )
                self._state.votes[agent_id] = vote

            except asyncio.TimeoutError:
                self._state.votes[agent_id] = "[NO VOTE]"

        return self._state.votes.copy()

    async def _wait_for_vote(self, agent_id: str) -> str:
        """
        Wait for a vote from a specific agent.

        Args:
            agent_id: Agent to wait for

        Returns:
            The vote provided by the agent
        """
        # Placeholder implementation
        future = asyncio.Future()
        return await future

    async def check_consensus(self) -> Optional[str]:
        """
        Check if consensus has been reached.

        Returns:
            The agreed-upon option if consensus exists, None otherwise
        """
        if not self._state.votes:
            return None

        # Count votes
        vote_counts: dict[str, int] = {}
        for vote in self._state.votes.values():
            if vote not in ("[NO VOTE]", "[ABSTAIN]"):
                vote_counts[vote] = vote_counts.get(vote, 0) + 1

        if not vote_counts:
            return None

        # Check if any option has threshold percentage
        total_votes = sum(vote_counts.values())
        for option, count in vote_counts.items():
            if count / total_votes >= self._state.consensus_threshold:
                self._state.phase = DiscussionPhase.DECISION
                return option

        self._state.phase = DiscussionPhase.NO_CONSENSUS
        return None

    async def record_decision(
        self,
        title: str,
        description: str,
        proposed_by: str,
        options: list[dict[str, Any]],
        selected_option: Optional[dict[str, Any]] = None,
        rationale: Optional[str] = None,
    ) -> None:
        """
        Record a decision from the discussion.

        Args:
            title: Decision title
            description: Decision description
            proposed_by: Agent proposing the decision
            options: Available options
            selected_option: The option that was selected
            rationale: Rationale for the decision
        """
        from communication_server.db.meeting import DecisionDB

        decision = DecisionDB(
            title=title,
            description=description,
            context={"opinions": self._state.opinions, "votes": self._state.votes},
            proposed_by=proposed_by,
            options=options,
            status="approved" if selected_option else "no_consensus",
            meeting_id=self._meeting_id,
            selected_option=selected_option,
            rationale=rationale,
            decided_at=datetime.utcnow(),
        )

        # In a real implementation, this would be persisted to the database
        # For now, we'll create the decision object
        self._state.phase = DiscussionPhase.COMPLETED

    async def complete_discussion(self) -> Meeting:
        """
        Complete the discussion and end the meeting.

        Returns:
            The completed meeting
        """
        self._state.phase = DiscussionPhase.COMPLETED
        self._running = False

        # End discussion via service
        meeting = await self._discussion_service.end_discussion(self._meeting_id)

        # Notify all participants
        await self._ws_manager.broadcast_to_meeting(
            self._meeting_id,
            {
                "type": "discussion_completed",
                "meeting_id": str(self._meeting_id),
                "opinions": self._state.opinions,
                "votes": self._state.votes,
            },
        )

        return meeting

    @property
    def state(self) -> DiscussionCoordinatorState:
        """Get the current coordinator state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if the coordinator is running."""
        return self._running

    async def next_speaker(self) -> Optional[str]:
        """
        Move to the next speaker.

        Returns:
            The next speaker's agent ID, or None if all have spoken
        """
        return await self._discussion_service.next_speaker(self._meeting_id)

    async def get_current_speaker(self) -> Optional[str]:
        """
        Get the current speaker.

        Returns:
            Current speaker's agent ID, or None
        """
        return await self._discussion_service.get_current_speaker(self._meeting_id)
