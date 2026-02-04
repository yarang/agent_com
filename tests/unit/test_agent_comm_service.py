"""
Unit tests for SPEC-AGENT-COMM-001 service layer.

Tests the business logic services:
- AgentCommunicationService
- AgentMeetingService
- AgentDecisionService
- SequentialDiscussionAlgorithm
- TopicAnalyzer
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.agent_comm import (
    CommunicationCreate,
    CommunicationListResponse,
    CommunicationResponse,
    DecisionCreate,
    DecisionListResponse,
    DecisionResponse,
    MeetingCreate,
    MeetingMessageResponse,
    MeetingResponse,
    MeetingStatus,
    MeetingType,
    MessageType,
)
from communication_server.repositories.agent_comm import (
    AgentCommunicationRepository,
    AgentDecisionRepository,
    AgentMeetingRepository,
)
from communication_server.services.agent_comm import (
    AgentCommunicationService,
    AgentDecisionService,
    AgentMeetingService,
    SequentialDiscussionAlgorithm,
    TopicAnalyzer,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_communication_data() -> CommunicationCreate:
    """Sample communication creation data."""
    return CommunicationCreate(
        sender_id=uuid4(),
        receiver_id=uuid4(),
        message_content="Test message content",
        topic="test_topic",
    )


@pytest.fixture
def sample_meeting_data() -> MeetingCreate:
    """Sample meeting creation data."""
    return MeetingCreate(
        topic="Test Meeting Topic",
        meeting_type=MeetingType.USER_SPECIFIED,
        participant_ids=[uuid4(), uuid4(), uuid4()],
        max_discussion_rounds=3,
    )


@pytest.fixture
def sample_decision_data() -> DecisionCreate:
    """Sample decision creation data."""
    return DecisionCreate(
        meeting_id=uuid4(),
        decision_content="Test decision content",
        rationale="Test rationale",
        related_communication_ids=[uuid4(), uuid4()],
        participant_agreement={"agent1": True, "agent2": True},
    )


# ============================================================================
# AgentCommunicationService Tests
# ============================================================================


class TestAgentCommunicationService:
    """Tests for AgentCommunicationService."""

    @pytest.mark.asyncio
    async def test_log_communication_success(
        self, sample_communication_data: CommunicationCreate
    ) -> None:
        """Test successful communication logging."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentCommunicationRepository)
        mock_repository.create = AsyncMock(
            return_value=CommunicationResponse(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                sender_id=sample_communication_data.sender_id,
                receiver_id=sample_communication_data.receiver_id,
                message_content=sample_communication_data.message_content,
                topic=sample_communication_data.topic,
                created_at=datetime.now(UTC),
            )
        )

        service = AgentCommunicationService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.log_communication(sample_communication_data)

        # Assert
        assert isinstance(result, CommunicationResponse)
        assert result.sender_id == sample_communication_data.sender_id
        assert result.receiver_id == sample_communication_data.receiver_id
        assert result.message_content == sample_communication_data.message_content
        mock_repository.create.assert_called_once_with(sample_communication_data)

    @pytest.mark.asyncio
    async def test_log_communication_size_exceeded(
        self, sample_communication_data: CommunicationCreate
    ) -> None:
        """Test communication logging with oversized message."""
        # Setup - Create message larger than 10MB
        large_message = "x" * (11 * 1024 * 1024)  # 11MB
        sample_communication_data.message_content = large_message

        mock_session = AsyncMock(spec=AsyncSession)
        service = AgentCommunicationService(mock_session)

        # Execute & Assert
        with pytest.raises(ValueError, match="exceeds maximum size"):
            await service.log_communication(sample_communication_data)

    @pytest.mark.asyncio
    async def test_query_communications_with_filters(
        self, sample_communication_data: CommunicationCreate
    ) -> None:
        """Test querying communications with filters."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentCommunicationRepository)
        mock_repository.list_with_filters = AsyncMock(
            return_value=(
                [
                    CommunicationResponse(
                        id=uuid4(),
                        timestamp=datetime.now(UTC),
                        sender_id=sample_communication_data.sender_id,
                        receiver_id=sample_communication_data.receiver_id,
                        message_content="Test message",
                        topic="test",
                        created_at=datetime.now(UTC),
                    )
                ],
                1,
            )
        )

        service = AgentCommunicationService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.query_communications(
            sender_id=sample_communication_data.sender_id,
            topic="test",
            page=1,
            page_size=50,
        )

        # Assert
        assert isinstance(result, CommunicationListResponse)
        assert len(result.communications) == 1
        assert result.total == 1
        assert result.page == 1
        mock_repository.list_with_filters.assert_called_once()


# ============================================================================
# AgentMeetingService Tests
# ============================================================================


class TestAgentMeetingService:
    """Tests for AgentMeetingService."""

    @pytest.mark.asyncio
    async def test_create_meeting_success(self, sample_meeting_data: MeetingCreate) -> None:
        """Test successful meeting creation."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentMeetingRepository)
        mock_repository.create_meeting = AsyncMock(
            return_value=MeetingResponse(
                id=uuid4(),
                topic=sample_meeting_data.topic,
                meeting_type=sample_meeting_data.meeting_type,
                status=MeetingStatus.PENDING,
                created_at=datetime.now(UTC),
                started_at=None,
                completed_at=None,
                max_discussion_rounds=sample_meeting_data.max_discussion_rounds,
                current_round=0,
            )
        )

        service = AgentMeetingService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.create_meeting(sample_meeting_data)

        # Assert
        assert isinstance(result, MeetingResponse)
        assert result.topic == sample_meeting_data.topic
        assert result.status == MeetingStatus.PENDING
        assert result.current_round == 0
        mock_repository.create_meeting.assert_called_once_with(sample_meeting_data)

    @pytest.mark.asyncio
    async def test_create_meeting_insufficient_participants(self) -> None:
        """Test meeting creation with insufficient participants."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        meeting_data = MeetingCreate(
            topic="Test",
            meeting_type=MeetingType.USER_SPECIFIED,
            participant_ids=[uuid4()],  # Only 1 participant
        )

        service = AgentMeetingService(mock_session)

        # Execute & Assert
        with pytest.raises(ValueError, match="At least 2 participants"):
            await service.create_meeting(meeting_data)

    @pytest.mark.asyncio
    async def test_start_meeting(self) -> None:
        """Test starting a meeting."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentMeetingRepository)
        meeting_id = uuid4()

        mock_repository.update_status = AsyncMock(
            return_value=MeetingResponse(
                id=meeting_id,
                topic="Test",
                meeting_type=MeetingType.USER_SPECIFIED,
                status=MeetingStatus.IN_PROGRESS,
                created_at=datetime.now(UTC),
                started_at=datetime.now(UTC),
                completed_at=None,
                max_discussion_rounds=3,
                current_round=0,
            )
        )

        service = AgentMeetingService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.start_meeting(meeting_id)

        # Assert
        assert result.status == MeetingStatus.IN_PROGRESS
        assert result.started_at is not None
        mock_repository.update_status.assert_called_once_with(meeting_id, MeetingStatus.IN_PROGRESS)

    @pytest.mark.asyncio
    async def test_complete_meeting(self) -> None:
        """Test completing a meeting."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentMeetingRepository)
        meeting_id = uuid4()

        mock_repository.update_status = AsyncMock(
            return_value=MeetingResponse(
                id=meeting_id,
                topic="Test",
                meeting_type=MeetingType.USER_SPECIFIED,
                status=MeetingStatus.COMPLETED,
                created_at=datetime.now(UTC),
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                max_discussion_rounds=3,
                current_round=1,
            )
        )

        service = AgentMeetingService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.complete_meeting(meeting_id)

        # Assert
        assert result.status == MeetingStatus.COMPLETED
        assert result.completed_at is not None
        mock_repository.update_status.assert_called_once_with(meeting_id, MeetingStatus.COMPLETED)


# ============================================================================
# AgentDecisionService Tests
# ============================================================================


class TestAgentDecisionService:
    """Tests for AgentDecisionService."""

    @pytest.mark.asyncio
    async def test_record_decision(self, sample_decision_data: DecisionCreate) -> None:
        """Test successful decision recording."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentDecisionRepository)
        mock_repository.create = AsyncMock(
            return_value=DecisionResponse(
                id=uuid4(),
                meeting_id=sample_decision_data.meeting_id,
                decision_content=sample_decision_data.decision_content,
                rationale=sample_decision_data.rationale,
                related_communication_ids=sample_decision_data.related_communication_ids,
                participant_agreement=sample_decision_data.participant_agreement,
                created_at=datetime.now(UTC),
            )
        )

        service = AgentDecisionService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.record_decision(sample_decision_data)

        # Assert
        assert isinstance(result, DecisionResponse)
        assert result.decision_content == sample_decision_data.decision_content
        mock_repository.create.assert_called_once_with(sample_decision_data)

    @pytest.mark.asyncio
    async def test_query_decisions(self) -> None:
        """Test querying decisions with filters."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentDecisionRepository)
        meeting_id = uuid4()

        mock_repository.list_with_filters = AsyncMock(
            return_value=(
                [
                    DecisionResponse(
                        id=uuid4(),
                        meeting_id=meeting_id,
                        decision_content="Test decision",
                        rationale="Test rationale",
                        related_communication_ids=[],
                        participant_agreement={},
                        created_at=datetime.now(UTC),
                    )
                ],
                1,
            )
        )

        service = AgentDecisionService(mock_session)
        service._repository = mock_repository

        # Execute
        result = await service.query_decisions(meeting_id=meeting_id)

        # Assert
        assert isinstance(result, DecisionListResponse)
        assert len(result.decisions) == 1
        assert result.total == 1
        mock_repository.list_with_filters.assert_called_once()


# ============================================================================
# SequentialDiscussionAlgorithm Tests
# ============================================================================


class TestSequentialDiscussionAlgorithm:
    """Tests for SequentialDiscussionAlgorithm."""

    @pytest.mark.asyncio
    async def test_start_discussion(self) -> None:
        """Test starting a discussion."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_meeting_service = AsyncMock(spec=AgentMeetingService)
        meeting_id = uuid4()

        mock_meeting_service.start_meeting = AsyncMock(
            return_value=MeetingResponse(
                id=meeting_id,
                topic="Test",
                meeting_type=MeetingType.USER_SPECIFIED,
                status=MeetingStatus.IN_PROGRESS,
                created_at=datetime.now(UTC),
                started_at=datetime.now(UTC),
                completed_at=None,
                max_discussion_rounds=3,
                current_round=0,
            )
        )

        algorithm = SequentialDiscussionAlgorithm(mock_session, mock_meeting_service)

        # Execute
        result = await algorithm.start_discussion(meeting_id)

        # Assert
        assert result.status == MeetingStatus.IN_PROGRESS
        assert len(algorithm._opinions) == 0
        assert len(algorithm._votes) == 0
        mock_meeting_service.start_meeting.assert_called_once_with(meeting_id)

    @pytest.mark.asyncio
    async def test_collect_opinion(self) -> None:
        """Test collecting an opinion from an agent."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_meeting_service = AsyncMock(spec=AgentMeetingService)
        meeting_id = uuid4()
        agent_id = uuid4()
        opinion = "This is my opinion"

        mock_meeting_service.record_message = AsyncMock(
            return_value=MeetingMessageResponse(
                id=uuid4(),
                meeting_id=meeting_id,
                agent_id=agent_id,
                message_content=opinion,
                message_type=MessageType.OPINION,
                sequence_number=1,
                timestamp=datetime.now(UTC),
            )
        )

        algorithm = SequentialDiscussionAlgorithm(mock_session, mock_meeting_service)

        # Execute
        result = await algorithm.collect_opinion(meeting_id, agent_id, opinion)

        # Assert
        assert result.message_content == opinion
        assert agent_id in algorithm._opinions
        assert algorithm._opinions[agent_id] == opinion
        mock_meeting_service.record_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_consensus_vote(self) -> None:
        """Test recording a consensus vote."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_meeting_service = AsyncMock(spec=AgentMeetingService)
        meeting_id = uuid4()
        agent_id = uuid4()

        mock_meeting_service.record_message = AsyncMock(
            return_value=MeetingMessageResponse(
                id=uuid4(),
                meeting_id=meeting_id,
                agent_id=agent_id,
                message_content=f"Agent {agent_id} agrees",
                message_type=MessageType.CONSENSUS,
                sequence_number=1,
                timestamp=datetime.now(UTC),
            )
        )

        algorithm = SequentialDiscussionAlgorithm(mock_session, mock_meeting_service)

        # Execute
        result = await algorithm.record_consensus_vote(meeting_id, agent_id, True)

        # Assert
        assert result.message_type == MessageType.CONSENSUS
        assert agent_id in algorithm._votes
        assert algorithm._votes[agent_id] is True

    @pytest.mark.asyncio
    async def test_check_consensus_all_agree(self) -> None:
        """Test consensus check when all agents agree."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_meeting_service = AsyncMock(spec=AgentMeetingService)

        algorithm = SequentialDiscussionAlgorithm(mock_session, mock_meeting_service)
        algorithm._votes = {uuid4(): True, uuid4(): True, uuid4(): True}

        # Execute
        result = await algorithm.check_consensus()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_consensus_not_all_agree(self) -> None:
        """Test consensus check when not all agents agree."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_meeting_service = AsyncMock(spec=AgentMeetingService)

        algorithm = SequentialDiscussionAlgorithm(mock_session, mock_meeting_service)
        algorithm._votes = {uuid4(): True, uuid4(): False, uuid4(): True}

        # Execute
        result = await algorithm.check_consensus()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_end_discussion(self) -> None:
        """Test ending a discussion."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_meeting_service = AsyncMock(spec=AgentMeetingService)
        meeting_id = uuid4()

        mock_meeting_service.complete_meeting = AsyncMock(
            return_value=MeetingResponse(
                id=meeting_id,
                topic="Test",
                meeting_type=MeetingType.USER_SPECIFIED,
                status=MeetingStatus.COMPLETED,
                created_at=datetime.now(UTC),
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                max_discussion_rounds=3,
                current_round=1,
            )
        )

        algorithm = SequentialDiscussionAlgorithm(mock_session, mock_meeting_service)

        # Execute
        result = await algorithm.end_discussion(meeting_id)

        # Assert
        assert result.status == MeetingStatus.COMPLETED
        mock_meeting_service.complete_meeting.assert_called_once_with(meeting_id)


# ============================================================================
# TopicAnalyzer Tests
# ============================================================================


class TestTopicAnalyzer:
    """Tests for TopicAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_communications(self) -> None:
        """Test analyzing communications for topics."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_repository = AsyncMock(spec=AgentCommunicationRepository)

        # Mock communication data
        communications = [
            CommunicationResponse(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                sender_id=uuid4(),
                receiver_id=uuid4(),
                message_content="Message 1 about API design",
                topic="api_design",
                created_at=datetime.now(UTC),
            ),
            CommunicationResponse(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                sender_id=uuid4(),
                receiver_id=uuid4(),
                message_content="Message 2 about API design",
                topic="api_design",
                created_at=datetime.now(UTC),
            ),
            CommunicationResponse(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                sender_id=uuid4(),
                receiver_id=uuid4(),
                message_content="Message about database",
                topic="database",
                created_at=datetime.now(UTC),
            ),
        ]

        mock_repository.list_with_filters = AsyncMock(return_value=(communications, 3))

        analyzer = TopicAnalyzer(mock_session)
        analyzer._comm_repository = mock_repository

        # Execute
        result = await analyzer.analyze_communications(time_range_hours=24, min_communications=1)

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 1

        # Check api_design topic (should have highest priority)
        api_topic = next((t for t in result if t["topic"] == "api_design"), None)
        assert api_topic is not None
        assert api_topic["communication_count"] == 2
        assert api_topic["priority"] > 0

    @pytest.mark.asyncio
    async def test_suggest_topics(self) -> None:
        """Test suggesting topics for a meeting."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)

        analyzer = TopicAnalyzer(mock_session)
        analyzer.analyze_communications = AsyncMock(
            return_value=[
                {
                    "topic": "API Design Discussion",
                    "priority": 0.8,
                    "reason": "5 communications in the last 24 hours",
                    "related_communications": [uuid4(), uuid4()],
                    "communication_count": 5,
                }
            ]
        )

        agent_ids = [uuid4(), uuid4(), uuid4()]

        # Execute
        result = await analyzer.suggest_topics(
            agent_ids=agent_ids, time_range_hours=24, max_topics=5
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["topic"] == "API Design Discussion"
        assert result[0]["priority"] == 0.8
