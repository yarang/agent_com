"""
Unit tests for enhanced DiscussionService with multi-round support.

Tests the new multi-round discussion functionality:
- Round tracking
- Consensus detection across rounds
- Round state management
- Vote recording
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from agent_comm_core.services.discussion import (
    DiscussionService,
    DiscussionState,
    RoundState,
)
from agent_comm_core.models.meeting import Meeting, MeetingStatus, MeetingParticipant


class MockMeetingRepository:
    """Mock repository for testing."""

    def __init__(self):
        self.meetings = {}
        self.participants = {}

    async def get_by_id(self, meeting_id: UUID) -> Meeting | None:
        return self.meetings.get(meeting_id)

    async def get_participants(self, meeting_id: UUID) -> list[MeetingParticipant]:
        return self.participants.get(meeting_id, [])

    async def update_status(self, meeting_id: UUID, status: MeetingStatus) -> Meeting:
        if meeting_id in self.meetings:
            self.meetings[meeting_id].status = status
        return self.meetings.get(meeting_id)


@pytest.mark.unit
class TestMultiRoundDiscussion:
    """Tests for multi-round discussion functionality."""

    @pytest.fixture
    def sample_meeting(self):
        """Create a sample meeting."""
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        repo = MockMeetingRepository()
        repo.meetings[meeting_id] = meeting
        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id,
                agent_id=aid,
                joined_at=datetime.utcnow(),
            )
            for aid in agent_ids
        ]

        return meeting_id, agent_ids, repo

    @pytest.mark.asyncio
    async def test_start_discussion_creates_first_round(self, sample_meeting):
        """Test that starting a discussion automatically creates the first round."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Verify first round was started
        assert meeting_id in service._discussions
        state = service._discussions[meeting_id]
        assert state.current_round == 1
        assert len(state.rounds) == 1
        assert state.rounds[0].round_number == 1
        assert state.rounds[0].started_at is not None
        assert state.rounds[0].completed_at is None

    @pytest.mark.asyncio
    async def test_complete_round_stores_round_state(self, sample_meeting):
        """Test that completing a round properly stores the round state."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Record some opinions and votes
        await service.record_opinion(meeting_id, agent_ids[0], "Option A")
        await service.record_opinion(meeting_id, agent_ids[1], "Option A")
        await service.record_opinion(meeting_id, agent_ids[2], "Option A")

        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option A")
        await service.record_vote(meeting_id, agent_ids[2], "Option A")

        # Complete the round
        completed_round = await service.complete_round(
            meeting_id,
            consensus_reached=True,
            consensus_option="Option A",
        )

        assert completed_round.round_number == 1
        assert completed_round.completed_at is not None
        assert completed_round.consensus_reached is True
        assert completed_round.consensus_option == "Option A"
        assert len(completed_round.opinions) == 3
        assert len(completed_round.votes) == 3

    @pytest.mark.asyncio
    async def test_start_second_round(self, sample_meeting):
        """Test starting a second round after completing the first."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Complete first round
        await service.record_opinion(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.complete_round(meeting_id, consensus_reached=False)

        # Start second round
        second_round = await service.start_round(meeting_id)

        assert second_round.round_number == 2
        state = service._discussions[meeting_id]
        assert state.current_round == 2
        assert len(state.rounds) == 2
        assert state.rounds[1].round_number == 2

        # Verify opinions and votes are reset for new round
        assert len(state.opinions) == 0
        assert len(state.votes) == 0

    @pytest.mark.asyncio
    async def test_cannot_exceed_max_rounds(self, sample_meeting):
        """Test that starting a round beyond max_rounds raises an error."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Complete all 3 rounds (default max_rounds)
        for i in range(3):
            await service.complete_round(meeting_id, consensus_reached=False)
            if i < 2:
                await service.start_round(meeting_id)

        # Try to start a 4th round
        with pytest.raises(ValueError, match="Maximum rounds"):
            await service.start_round(meeting_id)

    @pytest.mark.asyncio
    async def test_can_start_next_round(self, sample_meeting):
        """Test checking if another round can be started."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Can start next round
        assert await service.can_start_next_round(meeting_id) is True

        # Complete round 1
        await service.complete_round(meeting_id)

        # Still can start next round
        assert await service.can_start_next_round(meeting_id) is True

        # Start round 2
        await service.start_round(meeting_id)

        # Complete round 2
        await service.complete_round(meeting_id)

        # Start round 3 (last)
        await service.start_round(meeting_id)

        # Complete round 3
        await service.complete_round(meeting_id)

        # Cannot start more rounds
        assert await service.can_start_next_round(meeting_id) is False

    @pytest.mark.asyncio
    async def test_check_consensus_with_unanimous_agreement(self, sample_meeting):
        """Test consensus detection with unanimous agreement."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # All agents vote for Option A
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option A")
        await service.record_vote(meeting_id, agent_ids[2], "Option A")

        consensus_reached, consensus_option = await service.check_consensus(meeting_id)

        assert consensus_reached is True
        assert consensus_option == "Option A"

    @pytest.mark.asyncio
    async def test_check_consensus_with_threshold_not_met(self, sample_meeting):
        """Test consensus detection when threshold is not met."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # 2 out of 3 vote for Option A (67%, below 75% threshold)
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option A")
        await service.record_vote(meeting_id, agent_ids[2], "Option B")

        consensus_reached, consensus_option = await service.check_consensus(meeting_id)

        assert consensus_reached is False
        assert consensus_option is None

    @pytest.mark.asyncio
    async def test_check_consensus_ignores_abstentions(self, sample_meeting):
        """Test that abstentions are ignored in consensus calculation."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # 2 vote for Option A, 1 abstains
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option A")
        await service.record_vote(meeting_id, agent_ids[2], "[ABSTAIN]")

        # With 2 out of 2 valid votes, consensus should be reached
        consensus_reached, consensus_option = await service.check_consensus(meeting_id)

        assert consensus_reached is True
        assert consensus_option == "Option A"

    @pytest.mark.asyncio
    async def test_set_custom_consensus_threshold(self, sample_meeting):
        """Test setting a custom consensus threshold."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Set threshold to 100% (unanimous)
        await service.set_consensus_threshold(meeting_id, 1.0)

        state = service._discussions[meeting_id]
        assert state.consensus_threshold == 1.0

        # With 2 out of 3 votes, consensus should NOT be reached
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option A")
        await service.record_vote(meeting_id, agent_ids[2], "Option B")

        consensus_reached, _ = await service.check_consensus(meeting_id)
        assert consensus_reached is False

    @pytest.mark.asyncio
    async def test_set_invalid_consensus_threshold(self, sample_meeting):
        """Test that invalid thresholds are rejected."""
        meeting_id, _, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Threshold too high
        with pytest.raises(ValueError, match="Threshold must be between"):
            await service.set_consensus_threshold(meeting_id, 1.5)

        # Threshold too low
        with pytest.raises(ValueError, match="Threshold must be between"):
            await service.set_consensus_threshold(meeting_id, -0.1)

    @pytest.mark.asyncio
    async def test_get_round_state(self, sample_meeting):
        """Test retrieving state of a specific round."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Complete first round with some data
        await service.record_opinion(meeting_id, agent_ids[0], "Opinion 1")
        await service.record_vote(meeting_id, agent_ids[0], "Vote 1")
        await service.complete_round(meeting_id, consensus_reached=True)

        # Get round state
        round_state = await service.get_round_state(meeting_id, 1)

        assert round_state is not None
        assert round_state.round_number == 1
        assert round_state.consensus_reached is True
        assert round_state.opinions[agent_ids[0]] == "Opinion 1"
        assert round_state.votes[agent_ids[0]] == "Vote 1"

    @pytest.mark.asyncio
    async def test_get_round_state_nonexistent(self, sample_meeting):
        """Test getting state of a non-existent round."""
        meeting_id, _, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Try to get round 5 (doesn't exist)
        round_state = await service.get_round_state(meeting_id, 5)

        assert round_state is None

    @pytest.mark.asyncio
    async def test_get_current_round(self, sample_meeting):
        """Test getting the current round state."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Get current round (should be round 1)
        current = await service.get_current_round(meeting_id)

        assert current is not None
        assert current.round_number == 1
        assert current.completed_at is None

        # Complete the round
        await service.complete_round(meeting_id)

        # Current round should now show as completed
        current = await service.get_current_round(meeting_id)
        assert current.completed_at is not None

    @pytest.mark.asyncio
    async def test_get_round_history(self, sample_meeting):
        """Test getting the history of all rounds."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Complete first round
        await service.complete_round(meeting_id, consensus_reached=False)

        # Start and complete second round
        await service.start_round(meeting_id)
        await service.complete_round(meeting_id, consensus_reached=True)

        # Get round history
        history = await service.get_round_history(meeting_id)

        assert len(history) == 2
        assert history[0].round_number == 1
        assert history[0].consensus_reached is False
        assert history[1].round_number == 2
        assert history[1].consensus_reached is True

    @pytest.mark.asyncio
    async def test_round_state_preserves_separation(self, sample_meeting):
        """Test that each round maintains separate state."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Round 1: Vote for Option A
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option A")
        await service.complete_round(
            meeting_id, consensus_reached=True, consensus_option="Option A"
        )

        # Round 2: Vote for Option B (should be separate from round 1)
        await service.start_round(meeting_id)
        await service.record_vote(meeting_id, agent_ids[0], "Option B")
        await service.record_vote(meeting_id, agent_ids[1], "Option B")
        await service.complete_round(
            meeting_id, consensus_reached=True, consensus_option="Option B"
        )

        # Verify round 1 state
        round1 = await service.get_round_state(meeting_id, 1)
        assert round1.consensus_option == "Option A"
        assert round1.votes[agent_ids[0]] == "Option A"

        # Verify round 2 state
        round2 = await service.get_round_state(meeting_id, 2)
        assert round2.consensus_option == "Option B"
        assert round2.votes[agent_ids[0]] == "Option B"

    @pytest.mark.asyncio
    async def test_record_vote(self, sample_meeting):
        """Test recording votes during consensus phase."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Record votes
        await service.record_vote(meeting_id, agent_ids[0], "Option A")
        await service.record_vote(meeting_id, agent_ids[1], "Option B")
        await service.record_vote(meeting_id, agent_ids[2], "Option A")

        # Verify votes are stored
        state = service._discussions[meeting_id]
        assert state.votes[agent_ids[0]] == "Option A"
        assert state.votes[agent_ids[1]] == "Option B"
        assert state.votes[agent_ids[2]] == "Option A"

    @pytest.mark.asyncio
    async def test_end_discussion_preserves_round_history(self, sample_meeting):
        """Test that ending discussion preserves round history."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Complete two rounds
        await service.complete_round(meeting_id, consensus_reached=False)
        await service.start_round(meeting_id)
        await service.complete_round(meeting_id, consensus_reached=True)

        # End discussion
        await service.end_discussion(meeting_id)

        # Round history should be preserved even after discussion ends
        history = await service.get_round_history(meeting_id)

        assert len(history) == 2
        assert history[0].round_number == 1
        assert history[1].round_number == 2


@pytest.mark.unit
class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing functionality."""

    @pytest.fixture
    def sample_meeting(self):
        """Create a sample meeting."""
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4())]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        repo = MockMeetingRepository()
        repo.meetings[meeting_id] = meeting
        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id,
                agent_id=aid,
                joined_at=datetime.utcnow(),
            )
            for aid in agent_ids
        ]

        return meeting_id, agent_ids, repo

    @pytest.mark.asyncio
    async def test_opinions_still_work_with_multi_round(self, sample_meeting):
        """Test that the original opinion recording still works."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Record opinions using original method
        await service.record_opinion(meeting_id, agent_ids[0], "My opinion")
        await service.record_opinion(meeting_id, agent_ids[1], "Another opinion")

        # Verify opinions are accessible via original method
        opinions = await service.get_opinions(meeting_id)
        assert len(opinions) == 2
        assert opinions[agent_ids[0]] == "My opinion"
        assert opinions[agent_ids[1]] == "Another opinion"

    @pytest.mark.asyncio
    async def test_next_speaker_still_works(self, sample_meeting):
        """Test that speaker rotation still works with multi-round."""
        meeting_id, agent_ids, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Original next_speaker functionality should still work
        initial = await service.get_current_speaker(meeting_id)
        next_spk = await service.next_speaker(meeting_id)

        assert next_spk != initial
        assert await service.get_current_speaker(meeting_id) == next_spk

    @pytest.mark.asyncio
    async def test_is_discussion_active_includes_round_state(self, sample_meeting):
        """Test that discussion active check works with multi-round."""
        meeting_id, _, repo = sample_meeting

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Discussion should be active
        assert await service.is_discussion_active(meeting_id) is True

        # Complete all rounds
        await service.complete_round(meeting_id)
        await service.start_round(meeting_id)
        await service.complete_round(meeting_id)
        await service.start_round(meeting_id)
        await service.complete_round(meeting_id)

        # End discussion
        await service.end_discussion(meeting_id)

        # Discussion should no longer be active
        assert await service.is_discussion_active(meeting_id) is False
