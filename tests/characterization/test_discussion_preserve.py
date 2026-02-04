"""
Characterization tests for DiscussionService.

These tests capture the current behavior of the DiscussionService
to ensure that enhancements don't break existing functionality.
"""

from uuid import UUID, uuid4

import pytest

from agent_comm_core.models.meeting import Meeting, MeetingParticipant, MeetingStatus
from agent_comm_core.repositories.base import MeetingRepository
from agent_comm_core.services.discussion import DiscussionService


class MockMeetingRepository(MeetingRepository):
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

    async def create(self, meeting: Meeting) -> Meeting:
        self.meetings[meeting.id] = meeting
        return meeting

    async def update(self, meeting_id: UUID, **kwargs) -> Meeting | None:
        if meeting_id in self.meetings:
            meeting = self.meetings[meeting_id]
            for key, value in kwargs.items():
                setattr(meeting, key, value)
            return meeting
        return None


@pytest.mark.characterization
class TestDiscussionServiceCurrentBehavior:
    """Characterization tests for DiscussionService current behavior."""

    @pytest.mark.asyncio
    async def test_start_discussion_creates_state_characterize(self):
        """Characterize how discussion state is created when starting a discussion."""
        # Setup
        repo = MockMeetingRepository()
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.PENDING,
            created_at="2024-01-01T00:00:00Z",
        )
        await repo.create(meeting)

        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id, agent_id=aid, joined_at="2024-01-01T00:00:00Z"
            )
            for aid in agent_ids
        ]

        service = DiscussionService(repo)

        # Execute
        result = await service.start_discussion(meeting_id)

        # Verify current behavior
        assert meeting_id in service._discussions
        state = service._discussions[meeting_id]
        assert state.meeting_id == meeting_id
        assert state.started is True
        assert state.completed is False
        assert len(state.participants) == 3
        assert state.current_speaker == agent_ids[0]
        assert len(state.opinions) == 0
        assert result.status == MeetingStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_start_discussion_with_initial_speaker_characterize(self):
        """Characterize how initial speaker is set when starting discussion."""
        # Setup
        repo = MockMeetingRepository()
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        initial_speaker = agent_ids[2]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.PENDING,
            created_at="2024-01-01T00:00:00Z",
        )
        await repo.create(meeting)

        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id, agent_id=aid, joined_at="2024-01-01T00:00:00Z"
            )
            for aid in agent_ids
        ]

        service = DiscussionService(repo)

        # Execute
        result = await service.start_discussion(meeting_id, initial_speaker_id=initial_speaker)

        # Verify current behavior
        state = service._discussions[meeting_id]
        assert state.current_speaker == initial_speaker
        # Participants deque should be rotated to start with initial speaker
        assert list(state.participants)[0] == initial_speaker

    @pytest.mark.asyncio
    async def test_next_speaker_rotation_characterize(self):
        """Characterize how speaker rotation works."""
        # Setup
        repo = MockMeetingRepository()
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
        )
        await repo.create(meeting)

        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id, agent_id=aid, joined_at="2024-01-01T00:00:00Z"
            )
            for aid in agent_ids
        ]

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Get initial speaker
        initial_speaker = await service.get_current_speaker(meeting_id)

        # Execute - move to next speaker
        next_speaker = await service.next_speaker(meeting_id)

        # Verify current behavior
        assert next_speaker is not None
        assert next_speaker != initial_speaker
        # After first rotation, current_speaker should be the second participant
        current = await service.get_current_speaker(meeting_id)
        assert current == agent_ids[1]

    @pytest.mark.asyncio
    async def test_record_opinion_characterize(self):
        """Characterize how opinions are recorded."""
        # Setup
        repo = MockMeetingRepository()
        meeting_id = uuid4()
        agent_id = str(uuid4())
        opinion = "This is my opinion"

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
        )
        await repo.create(meeting)

        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id, agent_id=agent_id, joined_at="2024-01-01T00:00:00Z"
            )
        ]

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Execute
        await service.record_opinion(meeting_id, agent_id, opinion)

        # Verify current behavior
        opinions = await service.get_opinions(meeting_id)
        assert agent_id in opinions
        assert opinions[agent_id] == opinion

    @pytest.mark.asyncio
    async def test_end_discussion_characterize(self):
        """Characterize how discussion is ended."""
        # Setup
        repo = MockMeetingRepository()
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4())]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
        )
        await repo.create(meeting)

        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id, agent_id=aid, joined_at="2024-01-01T00:00:00Z"
            )
            for aid in agent_ids
        ]

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Execute
        result = await service.end_discussion(meeting_id)

        # Verify current behavior
        assert meeting_id not in service._discussions
        assert result.status == MeetingStatus.COMPLETED
        assert await service.is_discussion_active(meeting_id) is False

    @pytest.mark.asyncio
    async def test_create_decision_from_opinions_characterize(self):
        """Characterize how decisions are created from opinions."""
        # Setup
        repo = MockMeetingRepository()
        meeting_id = uuid4()
        agent_ids = [str(uuid4()), str(uuid4())]

        meeting = Meeting(
            id=meeting_id,
            title="Test Meeting",
            status=MeetingStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
        )
        await repo.create(meeting)

        repo.participants[meeting_id] = [
            MeetingParticipant(
                meeting_id=meeting_id, agent_id=aid, joined_at="2024-01-01T00:00:00Z"
            )
            for aid in agent_ids
        ]

        service = DiscussionService(repo)
        await service.start_discussion(meeting_id)

        # Record opinions
        await service.record_opinion(meeting_id, agent_ids[0], "Option A")
        await service.record_opinion(meeting_id, agent_ids[1], "Option A")

        # Execute
        decision = await service.create_decision(
            meeting_id=meeting_id,
            title="Test Decision",
            description="Test description",
            proposed_by=agent_ids[0],
            options=[{"title": "Option A"}, {"title": "Option B"}],
        )

        # Verify current behavior
        assert decision.title == "Test Decision"
        assert decision.description == "Test description"
        assert decision.proposed_by == agent_ids[0]
        assert "opinions" in decision.context
        assert decision.context["opinions"][agent_ids[0]] == "Option A"
