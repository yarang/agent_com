"""
Integration tests for Sequential Discussion Flow.

Tests the complete sequential discussion workflow:
- Create a meeting with multiple agents
- Connect agents via WebSocket
- Run through sequential discussion rounds
- Verify opinions are recorded
- Test consensus reaching
- Test decision recording
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

from agent_comm_core.models.meeting import MeetingStatus, MeetingMessage
from communication_server.coordinator.discussion import (
    DiscussionCoordinator,
    DiscussionPhase,
    SpeakerState,
)
from communication_server.websocket.manager import ConnectionManager
from agent_comm_core.services.discussion import DiscussionService


@pytest.mark.integration
class TestSequentialDiscussionFlow:
    """Tests for sequential discussion flow with multiple agents."""

    async def test_create_meeting_with_multiple_agents(
        self,
        meeting_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test creating a meeting with multiple agents."""
        meeting = await meeting_service.create_meeting(
            title="Architecture Discussion",
            participant_ids=sample_agent_ids[:3],
            description="Discussion about system architecture",
            agenda=["Database choice", "API design", "Deployment strategy"],
        )

        assert meeting is not None
        assert meeting.title == "Architecture Discussion"
        assert meeting.status == MeetingStatus.PENDING

        # Verify participants were added
        participants = await meeting_service.get_participants(meeting.id)
        assert len(participants) == 3
        assert {p.agent_id for p in participants} == set(sample_agent_ids[:3])

        await clean_db.commit()

    async def test_start_discussion_coordinator(
        self,
        active_meeting,
        meeting_service,
        connection_manager,
        clean_db,
    ):
        """Test starting the discussion coordinator."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)

        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=connection_manager,
            discussion_service=discussion_service,
            timeout_seconds=300,
        )

        # Start the discussion
        meeting = await coordinator.start(initial_question="What should be our first priority?")

        assert meeting.status == MeetingStatus.ACTIVE
        assert coordinator.state.phase == DiscussionPhase.OPINION_COLLECTION
        assert coordinator.state.current_question == "What should be our first priority?"
        assert len(coordinator.state.speakers) == 3

    async def test_sequential_opinion_collection(
        self,
        active_meeting,
        meeting_service,
        clean_db,
        sample_agent_ids,
    ):
        """Test collecting opinions from agents sequentially."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
        )

        await coordinator.start("What database should we use?")

        # Mock the wait_for_opinion to return opinions
        opinions = {
            sample_agent_ids[0]: "I recommend PostgreSQL for reliability",
            sample_agent_ids[1]: "PostgreSQL is good, but MongoDB might be faster",
            sample_agent_ids[2]: "Let's stick with PostgreSQL for ACID compliance",
        }

        async def mock_wait_opinion(agent_id: str) -> str:
            # Simulate network delay
            await asyncio.sleep(0.01)
            return opinions.get(agent_id, "No opinion")

        coordinator._wait_for_opinion = mock_wait_opinion

        # Collect opinions
        collected = await coordinator.request_opinions(
            question="What database should we use?",
            context={"options": ["PostgreSQL", "MongoDB", "Redis"]},
        )

        assert len(collected) == 3
        assert collected[sample_agent_ids[0]] == opinions[sample_agent_ids[0]]
        assert collected[sample_agent_ids[1]] == opinions[sample_agent_ids[1]]
        assert collected[sample_agent_ids[2]] == opinions[sample_agent_ids[2]]

        # Verify opinions were stored in coordinator state
        assert coordinator.state.opinions == collected

    async def test_consensus_building_phase(
        self,
        active_meeting,
        clean_db,
    ):
        """Test the consensus building phase with voting."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
        )

        # Pre-populate opinions
        coordinator.state.opinions = {
            "agent-001": "PostgreSQL",
            "agent-002": "PostgreSQL",
            "agent-003": "MongoDB",
        }

        # Mock voting
        votes = {
            "agent-001": "PostgreSQL",
            "agent-002": "PostgreSQL",
            "agent-003": "PostgreSQL",
        }

        async def mock_wait_vote(agent_id: str) -> str:
            await asyncio.sleep(0.01)
            return votes.get(agent_id, "Abstain")

        coordinator._wait_for_vote = mock_wait_vote

        # Facilitate consensus
        collected_votes = await coordinator.facilitate_consensus(
            proposal="We should use PostgreSQL as our database",
            options=["PostgreSQL", "MongoDB", "MySQL"],
        )

        assert len(collected_votes) == 3
        assert collected_votes["agent-001"] == "PostgreSQL"
        assert collected_votes["agent-002"] == "PostgreSQL"
        assert collected_votes["agent-003"] == "PostgreSQL"

    async def test_consensus_reached(
        self,
        active_meeting,
        clean_db,
    ):
        """Test checking if consensus was reached."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
            consensus_threshold=0.75,
        )

        # Set votes with consensus (3 out of 3 agree)
        coordinator.state.votes = {
            "agent-001": "Option A",
            "agent-002": "Option A",
            "agent-003": "Option A",
        }

        consensus = await coordinator.check_consensus()

        assert consensus == "Option A"
        assert coordinator.state.phase == DiscussionPhase.DECISION

    async def test_no_consensus_reached(
        self,
        active_meeting,
        clean_db,
    ):
        """Test scenario where no consensus is reached."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
            consensus_threshold=0.75,
        )

        # Set votes without consensus (split decision)
        coordinator.state.votes = {
            "agent-001": "Option A",
            "agent-002": "Option B",
            "agent-003": "Option A",
        }

        consensus = await coordinator.check_consensus()

        assert consensus is None
        assert coordinator.state.phase == DiscussionPhase.NO_CONSENSUS

    async def test_record_decision(
        self,
        active_meeting,
        clean_db,
    ):
        """Test recording a decision from discussion."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
        )

        # Pre-populate discussion data
        coordinator.state.opinions = {
            "agent-001": "We should use PostgreSQL",
            "agent-002": "I agree with PostgreSQL",
            "agent-003": "PostgreSQL it is",
        }
        coordinator.state.votes = {
            "agent-001": "PostgreSQL",
            "agent-002": "PostgreSQL",
            "agent-003": "PostgreSQL",
        }

        # Record decision
        await coordinator.record_decision(
            title="Database Choice",
            description="Select the primary database for the application",
            proposed_by="agent-001",
            options=[
                {"title": "PostgreSQL", "description": "Relational database"},
                {"title": "MongoDB", "description": "NoSQL database"},
            ],
            selected_option={"title": "PostgreSQL", "description": "Relational database"},
            rationale="Unanimous agreement on PostgreSQL for ACID compliance",
        )

        # In a real implementation, we'd verify the decision was persisted
        # For now, verify the phase changed
        assert coordinator.state.phase == DiscussionPhase.COMPLETED

    async def test_complete_discussion(
        self,
        active_meeting,
        clean_db,
        connection_manager,
    ):
        """Test completing a discussion and ending the meeting."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=connection_manager,
            discussion_service=discussion_service,
        )

        # Set up state
        coordinator.state.opinions = {"agent-001": "Yes", "agent-002": "Yes", "agent-003": "Yes"}
        coordinator.state.votes = {"agent-001": "Yes", "agent-002": "Yes", "agent-003": "Yes"}
        coordinator._running = True

        # Complete discussion
        meeting = await coordinator.complete_discussion()

        assert meeting.status == MeetingStatus.COMPLETED
        assert coordinator.state.phase == DiscussionPhase.COMPLETED
        assert coordinator.is_running is False

    async def test_websocket_broadcast_during_discussion(
        self,
        active_meeting,
        clean_db,
    ):
        """Test WebSocket broadcasts during discussion phases."""
        manager = ConnectionManager()
        broadcast_messages = []

        # Capture broadcast calls
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(meeting_id, message):
            broadcast_messages.append((meeting_id, message))

        manager.broadcast_to_meeting = mock_broadcast

        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=manager,
            discussion_service=discussion_service,
        )

        # Mock opinion waiting to return immediately
        async def mock_wait_opinion(agent_id):
            return f"Opinion from {agent_id}"

        coordinator._wait_for_opinion = mock_wait_opinion

        # Request opinions - should broadcast
        await coordinator.request_opinions("Test question?")

        # Verify broadcasts were made
        assert len(broadcast_messages) > 0
        assert any("opinion_request" in str(msg) for _, msg in broadcast_messages)


@pytest.mark.integration
class TestSpeakerOrderManagement:
    """Tests for managing speaker order in discussions."""

    async def test_speaker_rotation(
        self,
        active_meeting,
        clean_db,
    ):
        """Test rotating through speakers in order."""
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)

        # Start discussion
        await discussion_service.start_discussion(
            active_meeting.id,
            initial_speaker_id="agent-001",
        )

        # Get current speaker
        current = await discussion_service.get_current_speaker(active_meeting.id)
        assert current == "agent-001"

        # Move to next speaker
        next_speaker = await discussion_service.next_speaker(active_meeting.id)
        assert next_speaker == "agent-002"

        # Verify current changed
        current = await discussion_service.get_current_speaker(active_meeting.id)
        assert current == "agent-002"

    async def test_speaker_state_tracking(
        self,
        active_meeting,
        clean_db,
    ):
        """Test tracking state of each speaker."""
        from communication_server.coordinator.discussion import (
            DiscussionCoordinator,
            SpeakerState,
        )
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
        )

        await coordinator.start()

        # Verify initial speaker states
        assert len(coordinator.state.speaker_states) == 3

        for agent_id, state in coordinator.state.speaker_states.items():
            assert isinstance(state, SpeakerState)
            assert state.agent_id == agent_id
            assert state.has_spoken is False
            assert state.opinion is None


@pytest.mark.integration
class TestDiscussionTimeoutHandling:
    """Tests for timeout handling during discussions."""

    async def test_opinion_timeout(
        self,
        active_meeting,
        clean_db,
    ):
        """Test handling timeout when agent doesn't provide opinion."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
            timeout_seconds=1,  # Short timeout for testing
        )

        await coordinator.start()

        # Mock opinion wait to timeout
        async def mock_wait_opinion(agent_id):
            await asyncio.sleep(2)  # Longer than timeout
            return "Late response"

        coordinator._wait_for_opinion = mock_wait_opinion

        # Request opinions - should handle timeout
        opinions = await coordinator.request_opinions("Test question")

        # Verify timeout was handled with "[NO RESPONSE]"
        for agent_id, opinion in opinions.items():
            assert opinion == "[NO RESPONSE]"

    async def test_vote_timeout(
        self,
        active_meeting,
        clean_db,
    ):
        """Test handling timeout during consensus voting."""
        from communication_server.coordinator.discussion import DiscussionCoordinator
        from communication_server.services.discussion import DiscussionService
        from communication_server.repositories.meeting import SQLALchemyMeetingRepository

        repo = SQLALchemyMeetingRepository(clean_db)
        discussion_service = DiscussionService(repo)
        coordinator = DiscussionCoordinator(
            meeting_id=active_meeting.id,
            repository=repo,
            ws_manager=ConnectionManager(),
            discussion_service=discussion_service,
            timeout_seconds=1,
        )

        # Pre-populate opinions
        coordinator.state.opinions = {"agent-001": "Yes", "agent-002": "Yes", "agent-003": "Yes"}

        # Mock vote wait to timeout
        async def mock_wait_vote(agent_id):
            await asyncio.sleep(2)
            return "Late vote"

        coordinator._wait_for_vote = mock_wait_vote

        # Facilitate consensus - should handle timeout
        votes = await coordinator.facilitate_consensus(
            proposal="Test proposal",
            options=["A", "B"],
        )

        # Verify timeout was handled
        for agent_id, vote in votes.items():
            assert vote == "[NO VOTE]"
