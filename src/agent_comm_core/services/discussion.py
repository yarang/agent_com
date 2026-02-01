"""
Discussion service for sequential agent discussion logic.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from agent_comm_core.models.meeting import Meeting, MeetingStatus
from agent_comm_core.models.decision import Decision, DecisionCreate, DecisionStatus
from agent_comm_core.repositories.base import MeetingRepository


@dataclass
class DiscussionState:
    """State of an ongoing discussion."""

    meeting_id: UUID
    participants: deque[str] = field(default_factory=deque)
    current_speaker: Optional[str] = None
    opinions: dict[str, str] = field(default_factory=dict)
    started: bool = False
    completed: bool = False


class DiscussionService:
    """
    Service for managing sequential discussions between agents.

    Implements a round-robin discussion pattern where agents
    speak in order and can record opinions for decision making.
    """

    def __init__(self, meeting_repository: MeetingRepository) -> None:
        """
        Initialize the discussion service.

        Args:
            meeting_repository: Meeting repository instance
        """
        self._repository = meeting_repository
        self._discussions: dict[UUID, DiscussionState] = {}

    async def start_discussion(
        self, meeting_id: UUID, initial_speaker_id: Optional[str] = None
    ) -> Meeting:
        """
        Start a discussion for a meeting.

        Args:
            meeting_id: Meeting ID
            initial_speaker_id: Optional initial speaker (defaults to first participant)

        Returns:
            The updated meeting

        Raises:
            ValueError: If meeting not found or has no participants
        """
        meeting = await self._repository.get_by_id(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        participants = await self._repository.get_participants(meeting_id)
        if not participants:
            raise ValueError(f"Meeting {meeting_id} has no participants")

        # Create discussion state
        participant_ids = deque(p.agent_id for p in participants)
        current_speaker = initial_speaker_id or participant_ids[0]

        # Rotate to start with initial speaker
        if initial_speaker_id:
            while participant_ids and participant_ids[0] != initial_speaker_id:
                participant_ids.rotate(-1)

        self._discussions[meeting_id] = DiscussionState(
            meeting_id=meeting_id,
            participants=participant_ids,
            current_speaker=current_speaker,
            started=True,
        )

        # Update meeting status to active
        await self._repository.update_status(meeting_id, MeetingStatus.ACTIVE)

        return meeting

    async def next_speaker(self, meeting_id: UUID) -> Optional[str]:
        """
        Move to the next speaker in the discussion.

        Args:
            meeting_id: Meeting ID

        Returns:
            The next speaker's agent ID, or None if discussion is complete

        Raises:
            ValueError: If discussion not found
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        if not state.participants:
            state.completed = True
            await self._repository.update_status(meeting_id, MeetingStatus.COMPLETED)
            return None

        # Rotate to next speaker
        state.participants.rotate(-1)
        state.current_speaker = state.participants[0]

        return state.current_speaker

    async def get_current_speaker(self, meeting_id: UUID) -> Optional[str]:
        """
        Get the current speaker in a discussion.

        Args:
            meeting_id: Meeting ID

        Returns:
            Current speaker's agent ID, or None if no discussion
        """
        state = self._discussions.get(meeting_id)
        return state.current_speaker if state else None

    async def record_opinion(self, meeting_id: UUID, agent_id: str, opinion: str) -> None:
        """
        Record an agent's opinion during a discussion.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent identifier
            opinion: The agent's opinion

        Raises:
            ValueError: If discussion not found
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        state.opinions[agent_id] = opinion

    async def get_opinions(self, meeting_id: UUID) -> dict[str, str]:
        """
        Get all recorded opinions for a discussion.

        Args:
            meeting_id: Meeting ID

        Returns:
            Dictionary mapping agent IDs to their opinions

        Raises:
            ValueError: If discussion not found
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        return state.opinions.copy()

    async def create_decision(
        self,
        meeting_id: UUID,
        title: str,
        description: str,
        proposed_by: str,
        options: list[dict],
        context: Optional[dict] = None,
    ) -> Decision:
        """
        Create a decision from the discussion context.

        Args:
            meeting_id: Meeting ID
            title: Decision title
            description: Decision description
            proposed_by: Agent proposing the decision
            options: List of decision options
            context: Optional context dictionary

        Returns:
            The created decision model (not persisted to database)

        Raises:
            ValueError: If discussion not found or no opinions recorded
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        if not state.opinions:
            raise ValueError(f"No opinions recorded for meeting {meeting_id}")

        create_data = DecisionCreate(
            title=title,
            description=description,
            context=context or {"opinions": state.opinions},
            proposed_by=proposed_by,
            options=options,
            meeting_id=meeting_id,
        )

        # Return model instance (actual persistence would be in a DecisionService)
        return Decision(**create_data.model_dump(), status=DecisionStatus.PENDING)

    async def end_discussion(self, meeting_id: UUID) -> Meeting:
        """
        End a discussion and complete the meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            The completed meeting

        Raises:
            ValueError: If meeting not found
        """
        # Remove discussion state
        self._discussions.pop(meeting_id, None)

        # Update meeting status
        meeting = await self._repository.update_status(meeting_id, MeetingStatus.COMPLETED)

        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        return meeting

    async def is_discussion_active(self, meeting_id: UUID) -> bool:
        """
        Check if a discussion is currently active.

        Args:
            meeting_id: Meeting ID

        Returns:
            True if discussion is active, False otherwise
        """
        state = self._discussions.get(meeting_id)
        return state is not None and state.started and not state.completed
