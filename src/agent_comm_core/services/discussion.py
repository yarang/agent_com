"""
Discussion service for sequential agent discussion logic.

Enhanced with multi-round discussion support and consensus tracking.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from agent_comm_core.models.decision import Decision, DecisionCreate, DecisionStatus
from agent_comm_core.models.meeting import Meeting, MeetingStatus
from agent_comm_core.repositories.base import MeetingRepository


@dataclass
class RoundState:
    """State of a single discussion round."""

    round_number: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    opinions: dict[str, str] = field(default_factory=dict)
    consensus_reached: bool = False
    consensus_option: str | None = None
    votes: dict[str, str] = field(default_factory=dict)


@dataclass
class DiscussionState:
    """State of an ongoing discussion with multi-round support."""

    meeting_id: UUID
    participants: deque[str] = field(default_factory=deque)
    current_speaker: str | None = None
    opinions: dict[str, str] = field(default_factory=dict)
    votes: dict[str, str] = field(default_factory=dict)
    started: bool = False
    completed: bool = False
    current_round: int = 0
    max_rounds: int = 3
    rounds: list[RoundState] = field(default_factory=list)
    consensus_threshold: float = 0.75
    started_at: datetime | None = None


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
        self._completed_rounds: dict[UUID, list[RoundState]] = {}

    async def start_discussion(
        self, meeting_id: UUID, initial_speaker_id: str | None = None
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
            started_at=datetime.utcnow(),
        )

        # Start first round
        await self.start_round(meeting_id)

        # Update meeting status to active
        await self._repository.update_status(meeting_id, MeetingStatus.ACTIVE)

        return meeting

    async def next_speaker(self, meeting_id: UUID) -> str | None:
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

    async def get_current_speaker(self, meeting_id: UUID) -> str | None:
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
        context: dict | None = None,
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
        # Preserve round history before removing discussion state
        state = self._discussions.get(meeting_id)
        if state and state.rounds:
            self._completed_rounds[meeting_id] = state.rounds.copy()

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

    # ========================================================================
    # Multi-Round Discussion Methods
    # ========================================================================

    async def start_round(self, meeting_id: UUID) -> RoundState:
        """
        Start a new discussion round.

        Args:
            meeting_id: Meeting ID

        Returns:
            The new round state

        Raises:
            ValueError: If discussion not found or max rounds reached
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        if state.current_round >= state.max_rounds:
            raise ValueError(
                f"Maximum rounds ({state.max_rounds}) reached for meeting {meeting_id}"
            )

        # Increment round number
        state.current_round += 1

        # Create new round state
        round_state = RoundState(
            round_number=state.current_round,
            started_at=datetime.utcnow(),
        )
        state.rounds.append(round_state)

        # Reset current round opinions and votes
        state.opinions = {}
        state.votes = {}

        return round_state

    async def complete_round(
        self, meeting_id: UUID, consensus_reached: bool = False, consensus_option: str | None = None
    ) -> RoundState:
        """
        Complete the current discussion round.

        Args:
            meeting_id: Meeting ID
            consensus_reached: Whether consensus was reached
            consensus_option: The option that reached consensus

        Returns:
            The completed round state

        Raises:
            ValueError: If discussion not found or no active round
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        if not state.rounds:
            raise ValueError(f"No active round for meeting {meeting_id}")

        # Get current round
        current_round = state.rounds[-1]

        # Update round state
        current_round.completed_at = datetime.utcnow()
        current_round.opinions = state.opinions.copy()
        current_round.votes = state.votes.copy()
        current_round.consensus_reached = consensus_reached
        current_round.consensus_option = consensus_option

        return current_round

    async def check_consensus(self, meeting_id: UUID) -> tuple[bool, str | None]:
        """
        Check if consensus has been reached in the current round.

        Args:
            meeting_id: Meeting ID

        Returns:
            Tuple of (consensus_reached, consensus_option)

        Raises:
            ValueError: If discussion not found
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        if not state.votes:
            return False, None

        # Count votes
        vote_counts: dict[str, int] = {}
        for vote in state.votes.values():
            if vote not in ("[NO VOTE]", "[ABSTAIN]"):
                vote_counts[vote] = vote_counts.get(vote, 0) + 1

        if not vote_counts:
            return False, None

        # Check if any option has threshold percentage
        total_votes = sum(vote_counts.values())
        for option, count in vote_counts.items():
            if count / total_votes >= state.consensus_threshold:
                return True, option

        return False, None

    async def can_start_next_round(self, meeting_id: UUID) -> bool:
        """
        Check if another round can be started.

        Args:
            meeting_id: Meeting ID

        Returns:
            True if another round can be started, False otherwise
        """
        state = self._discussions.get(meeting_id)
        if not state:
            return False

        return state.current_round < state.max_rounds and not state.completed

    async def get_round_state(self, meeting_id: UUID, round_number: int) -> RoundState | None:
        """
        Get the state of a specific round.

        Args:
            meeting_id: Meeting ID
            round_number: Round number (1-indexed)

        Returns:
            The round state, or None if not found
        """
        state = self._discussions.get(meeting_id)
        if not state:
            return None

        for round_state in state.rounds:
            if round_state.round_number == round_number:
                return round_state

        return None

    async def get_current_round(self, meeting_id: UUID) -> RoundState | None:
        """
        Get the current round state.

        Args:
            meeting_id: Meeting ID

        Returns:
            The current round state, or None if no active round
        """
        state = self._discussions.get(meeting_id)
        if not state or not state.rounds:
            return None

        return state.rounds[-1]

    async def get_round_history(self, meeting_id: UUID) -> list[RoundState]:
        """
        Get the history of all rounds.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of round states
        """
        # First check active discussion
        state = self._discussions.get(meeting_id)
        if state:
            return state.rounds.copy()

        # Then check completed rounds
        return self._completed_rounds.get(meeting_id, [])

    async def set_consensus_threshold(self, meeting_id: UUID, threshold: float) -> None:
        """
        Set the consensus threshold for a discussion.

        Args:
            meeting_id: Meeting ID
            threshold: Consensus threshold (0.0 to 1.0)

        Raises:
            ValueError: If discussion not found or threshold invalid
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        state.consensus_threshold = threshold

    async def record_vote(self, meeting_id: UUID, agent_id: str, vote: str) -> None:
        """
        Record a vote during consensus phase.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent identifier
            vote: The agent's vote

        Raises:
            ValueError: If discussion not found
        """
        state = self._discussions.get(meeting_id)
        if not state:
            raise ValueError(f"No active discussion for meeting {meeting_id}")

        state.votes[agent_id] = vote
