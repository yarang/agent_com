"""
Service layer for SPEC-AGENT-COMM-001.

Provides business logic services for agent communication, meetings, and decisions.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.agent_comm import (
    CommunicationCreate,
    CommunicationListResponse,
    CommunicationResponse,
    DecisionCreate,
    DecisionListResponse,
    DecisionResponse,
    MeetingCreate,
    MeetingDetailResponse,
    MeetingMessageCreate,
    MeetingMessageResponse,
    MeetingParticipantResponse,
    MeetingResponse,
    MeetingStatus,
)
from communication_server.repositories.agent_comm import (
    AgentCommunicationRepository,
    AgentDecisionRepository,
    AgentMeetingRepository,
)


class AgentCommunicationService:
    """
    Service for agent communications.

    Provides high-level operations for logging and querying communications.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._repository = AgentCommunicationRepository(session)

    async def log_communication(self, data: CommunicationCreate) -> CommunicationResponse:
        """
        Log a communication between agents.

        Args:
            data: Communication creation data

        Returns:
            The logged communication

        Raises:
            ValueError: If message content exceeds maximum size
        """
        # Validate message size (10MB limit as per SPEC)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        content_size = len(data.message_content.encode("utf-8"))
        if content_size > max_size:
            raise ValueError(f"Message content exceeds maximum size of {max_size} bytes")

        return await self._repository.create(data)

    async def get_communication(self, communication_id: UUID) -> CommunicationResponse | None:
        """
        Get a communication by ID.

        Args:
            communication_id: Communication ID

        Returns:
            The communication if found, None otherwise
        """
        return await self._repository.get_by_id(communication_id)

    async def query_communications(
        self,
        sender_id: UUID | None = None,
        receiver_id: UUID | None = None,
        topic: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> CommunicationListResponse:
        """
        Query communications with filters and pagination.

        Args:
            sender_id: Optional sender filter
            receiver_id: Optional receiver filter
            topic: Optional topic filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Paginated list of communications
        """
        offset = (page - 1) * page_size
        communications, total = await self._repository.list_with_filters(
            sender_id=sender_id,
            receiver_id=receiver_id,
            topic=topic,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )

        return CommunicationListResponse(
            communications=communications,
            total=total,
            page=page,
            page_size=page_size,
        )


class AgentMeetingService:
    """
    Service for agent meetings.

    Provides high-level operations for creating and managing meetings.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._repository = AgentMeetingRepository(session)

    async def create_meeting(self, data: MeetingCreate) -> MeetingResponse:
        """
        Create a new meeting.

        Args:
            data: Meeting creation data

        Returns:
            The created meeting

        Raises:
            ValueError: If participant list is invalid
        """
        if len(data.participant_ids) < 2:
            raise ValueError("At least 2 participants are required for a meeting")

        return await self._repository.create_meeting(data)

    async def get_meeting(self, meeting_id: UUID) -> MeetingResponse | None:
        """
        Get a meeting by ID.

        Args:
            meeting_id: Meeting ID

        Returns:
            The meeting if found, None otherwise
        """
        return await self._repository.get_by_id(meeting_id)

    async def get_meeting_detail(self, meeting_id: UUID) -> MeetingDetailResponse | None:
        """
        Get detailed meeting information including participants and messages.

        Args:
            meeting_id: Meeting ID

        Returns:
            Detailed meeting information if found, None otherwise
        """
        meeting = await self._repository.get_by_id(meeting_id)
        if not meeting:
            return None

        participants = await self._repository.get_participants(meeting_id)
        messages = await self._repository.get_messages(meeting_id)

        # Get decision if any
        decision_repo = AgentDecisionRepository(self._session)
        decisions = await decision_repo.get_by_meeting(meeting_id)
        decision = decisions[0] if decisions else None

        return MeetingDetailResponse(
            id=meeting.id,
            topic=meeting.topic,
            meeting_type=meeting.meeting_type,
            status=meeting.status,
            created_at=meeting.created_at,
            started_at=meeting.started_at,
            completed_at=meeting.completed_at,
            max_discussion_rounds=meeting.max_discussion_rounds,
            current_round=meeting.current_round,
            participant_ids=[p.agent_id for p in participants],
            participants=participants,
            messages=messages,
            decision=decision,
        )

    async def start_meeting(self, meeting_id: UUID) -> MeetingResponse | None:
        """
        Start a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            The updated meeting if found, None otherwise
        """
        return await self._repository.update_status(meeting_id, MeetingStatus.IN_PROGRESS)

    async def complete_meeting(self, meeting_id: UUID) -> MeetingResponse | None:
        """
        Complete a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            The updated meeting if found, None otherwise
        """
        return await self._repository.update_status(meeting_id, MeetingStatus.COMPLETED)

    async def fail_meeting(self, meeting_id: UUID) -> MeetingResponse | None:
        """
        Mark a meeting as failed.

        Args:
            meeting_id: Meeting ID

        Returns:
            The updated meeting if found, None otherwise
        """
        return await self._repository.update_status(meeting_id, MeetingStatus.FAILED)

    async def add_participant(
        self,
        meeting_id: UUID,
        agent_id: UUID,
        role: str = "participant",
    ) -> MeetingParticipantResponse:
        """
        Add a participant to a meeting.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent ID
            role: Participant role

        Returns:
            The added participant
        """
        from agent_comm_core.models.agent_comm import MeetingParticipantCreate

        data = MeetingParticipantCreate(agent_id=agent_id, role=role)
        return await self._repository.add_participant(meeting_id, data)

    async def get_participants(self, meeting_id: UUID) -> list[MeetingParticipantResponse]:
        """
        Get all participants for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of meeting participants
        """
        return await self._repository.get_participants(meeting_id)

    async def get_participants_ordered(self, meeting_id: UUID) -> list[MeetingParticipantResponse]:
        """
        Get participants in speaking order.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of participants ordered by speaking_order
        """
        participants = await self._repository.get_participants(meeting_id)
        return sorted(participants, key=lambda p: p.speaking_order or 0)

    async def record_message(self, data: MeetingMessageCreate) -> MeetingMessageResponse:
        """
        Record a message in a meeting.

        Args:
            data: Message creation data

        Returns:
            The recorded message
        """
        return await self._repository.create_message(data)

    async def get_messages(
        self,
        meeting_id: UUID,
        limit: int = 100,
    ) -> list[MeetingMessageResponse]:
        """
        Get messages from a meeting.

        Args:
            meeting_id: Meeting ID
            limit: Maximum number of messages

        Returns:
            List of meeting messages
        """
        return await self._repository.get_messages(meeting_id, limit)

    async def next_round(self, meeting_id: UUID) -> MeetingResponse | None:
        """
        Increment the discussion round.

        Args:
            meeting_id: Meeting ID

        Returns:
            The updated meeting if found, None otherwise
        """
        return await self._repository.increment_round(meeting_id)


class AgentDecisionService:
    """
    Service for agent decisions.

    Provides high-level operations for recording and querying decisions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._repository = AgentDecisionRepository(session)

    async def record_decision(self, data: DecisionCreate) -> DecisionResponse:
        """
        Record a decision.

        Args:
            data: Decision creation data

        Returns:
            The recorded decision
        """
        return await self._repository.create(data)

    async def get_decision(self, decision_id: UUID) -> DecisionResponse | None:
        """
        Get a decision by ID.

        Args:
            decision_id: Decision ID

        Returns:
            The decision if found, None otherwise
        """
        # Need to implement get_by_id in repository
        # For now, use meeting-based lookup
        return None

    async def get_meeting_decisions(self, meeting_id: UUID) -> list[DecisionResponse]:
        """
        Get all decisions for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of decisions for the meeting
        """
        return await self._repository.get_by_meeting(meeting_id)

    async def query_decisions(
        self,
        meeting_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DecisionListResponse:
        """
        Query decisions with filters and pagination.

        Args:
            meeting_id: Optional meeting filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Paginated list of decisions
        """
        offset = (page - 1) * page_size
        decisions, total = await self._repository.list_with_filters(
            meeting_id=meeting_id,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )

        return DecisionListResponse(
            decisions=decisions,
            total=total,
            page=page,
            page_size=page_size,
        )


class SequentialDiscussionAlgorithm:
    """
    Sequential discussion algorithm for agent meetings.

    Implements the discussion flow as specified in SPEC-AGENT-COMM-001:
    1. Determine speaking order
    2. Collect opinions sequentially
    3. Facilitate consensus phase
    4. Record decision or continue to next round
    """

    def __init__(
        self,
        session: AsyncSession,
        meeting_service: AgentMeetingService,
        timeout_seconds: int = 300,
    ) -> None:
        """
        Initialize the discussion algorithm.

        Args:
            session: SQLAlchemy async session
            meeting_service: Meeting service instance
            timeout_seconds: Timeout for each agent response
        """
        self._session = session
        self._meeting_service = meeting_service
        self._timeout_seconds = timeout_seconds
        self._opinions: dict[UUID, str] = {}
        self._votes: dict[UUID, bool] = {}

    async def start_discussion(
        self,
        meeting_id: UUID,
        initial_speaker_id: UUID | None = None,
    ) -> MeetingResponse:
        """
        Start a discussion.

        Args:
            meeting_id: Meeting ID
            initial_speaker_id: Optional initial speaker ID

        Returns:
            The started meeting
        """
        meeting = await self._meeting_service.start_meeting(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # Reset state
        self._opinions = {}
        self._votes = {}

        return meeting

    async def collect_opinion(
        self,
        meeting_id: UUID,
        agent_id: UUID,
        opinion: str,
    ) -> MeetingMessageResponse:
        """
        Collect an opinion from an agent.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent ID
            opinion: Agent's opinion

        Returns:
            The recorded message
        """
        from agent_comm_core.models.agent_comm import MeetingMessageCreate, MessageType

        data = MeetingMessageCreate(
            meeting_id=meeting_id,
            agent_id=agent_id,
            message_content=opinion,
            message_type=MessageType.OPINION,
        )

        message = await self._meeting_service.record_message(data)
        self._opinions[agent_id] = opinion

        return message

    async def record_consensus_vote(
        self,
        meeting_id: UUID,
        agent_id: UUID,
        agrees: bool,
    ) -> MeetingMessageResponse:
        """
        Record a consensus vote from an agent.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent ID
            agrees: Whether the agent agrees

        Returns:
            The recorded message
        """
        from agent_comm_core.models.agent_comm import MeetingMessageCreate, MessageType

        content = f"Agent {agent_id} {'agrees' if agrees else 'disagrees'}"
        data = MeetingMessageCreate(
            meeting_id=meeting_id,
            agent_id=agent_id,
            message_content=content,
            message_type=MessageType.CONSENSUS,
        )

        message = await self._meeting_service.record_message(data)
        self._votes[agent_id] = agrees

        return message

    async def check_consensus(self) -> bool:
        """
        Check if consensus has been reached.

        Returns:
            True if all agents agree, False otherwise
        """
        if not self._votes:
            return False

        return all(self._votes.values())

    async def get_next_speaker(self, meeting_id: UUID) -> UUID | None:
        """
        Get the next speaker in the discussion.

        Args:
            meeting_id: Meeting ID

        Returns:
            The next speaker's agent ID, or None if all have spoken
        """
        participants = await self._meeting_service.get_participants_ordered(meeting_id)
        spoken_agents = set(self._opinions.keys())

        for participant in participants:
            if participant.agent_id not in spoken_agents:
                return participant.agent_id

        return None

    async def get_current_speaker(self, meeting_id: UUID) -> UUID | None:
        """
        Get the current speaker in the discussion.

        Args:
            meeting_id: Meeting ID

        Returns:
            The current speaker's agent ID, or None
        """
        participants = await self._meeting_service.get_participants_ordered(meeting_id)
        spoken_agents = set(self._opinions.keys())

        for participant in participants:
            if participant.agent_id not in spoken_agents:
                return participant.agent_id

        # All have spoken
        return None

    async def end_discussion(self, meeting_id: UUID) -> MeetingResponse:
        """
        End the discussion.

        Args:
            meeting_id: Meeting ID

        Returns:
            The completed meeting
        """
        return await self._meeting_service.complete_meeting(meeting_id)

    def get_collected_opinions(self) -> dict[UUID, str]:
        """Get all collected opinions."""
        return self._opinions.copy()

    def get_collected_votes(self) -> dict[UUID, bool]:
        """Get all collected votes."""
        return self._votes.copy()


class TopicAnalyzer:
    """
    Service for analyzing communications and suggesting meeting topics.

    Analyzes recent communication logs to identify topics requiring discussion.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the analyzer.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._comm_repository = AgentCommunicationRepository(session)

    async def analyze_communications(
        self,
        time_range_hours: int = 24,
        agent_filter: set[UUID] | None = None,
        min_communications: int = 3,
    ) -> list[dict]:
        """
        Analyze communications for topic suggestions.

        Args:
            time_range_hours: Time range to analyze in hours
            agent_filter: Optional set of agent IDs to filter by
            min_communications: Minimum communications to consider a topic

        Returns:
            List of topic suggestions with metadata
        """
        from datetime import timedelta

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=time_range_hours)

        communications, _ = await self._comm_repository.list_with_filters(
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        # Filter by agent if specified
        if agent_filter:
            communications = [
                c
                for c in communications
                if c.sender_id in agent_filter or c.receiver_id in agent_filter
            ]

        # Group by topic
        topic_groups: dict[str, list[CommunicationResponse]] = {}
        for comm in communications:
            topic = comm.topic or "general"
            if topic not in topic_groups:
                topic_groups[topic] = []
            topic_groups[topic].append(comm)

        # Analyze topics
        suggestions = []
        for topic, comms in topic_groups.items():
            if len(comms) >= min_communications:
                # Calculate priority based on frequency and recency
                priority = min(1.0, len(comms) / 10.0)

                suggestions.append(
                    {
                        "topic": topic,
                        "priority": priority,
                        "reason": f"{len(comms)} communications in the last {time_range_hours} hours",
                        "related_communications": [c.id for c in comms],
                        "communication_count": len(comms),
                    }
                )

        # Sort by priority descending
        suggestions.sort(key=lambda x: x["priority"], reverse=True)

        return suggestions

    async def suggest_topics(
        self,
        agent_ids: list[UUID],
        time_range_hours: int = 24,
        max_topics: int = 5,
    ) -> list[dict]:
        """
        Suggest topics for a meeting.

        Args:
            agent_ids: List of agent IDs to analyze
            time_range_hours: Time range to analyze in hours
            max_topics: Maximum number of topics to suggest

        Returns:
            List of topic suggestions
        """
        agent_filter = set(agent_ids)
        suggestions = await self.analyze_communications(
            time_range_hours=time_range_hours,
            agent_filter=agent_filter,
        )

        return suggestions[:max_topics]


__all__ = [
    "AgentCommunicationService",
    "AgentMeetingService",
    "AgentDecisionService",
    "SequentialDiscussionAlgorithm",
    "TopicAnalyzer",
]
