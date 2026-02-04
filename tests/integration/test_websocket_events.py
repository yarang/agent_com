"""
Integration tests for enhanced WebSocket events.

Tests the comprehensive event broadcasting and reconnection handling:
- agent_joined events
- opinion_presented events
- consensus_reached events
- round_started and round_completed events
- reconnection handling
- state synchronization
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agent_comm_core.models.auth import Agent
from agent_comm_core.services.discussion import DiscussionState, RoundState
from communication_server.websocket.handler import (
    MeetingEvent,
    MessageType,
    WebSocketHandler,
)
from communication_server.websocket.manager import ConnectionManager


@pytest.mark.integration
class TestWebSocketEventBroadcasting:
    """Tests for WebSocket event broadcasting."""

    @pytest.fixture
    def setup_handler(self):
        """Set up handler and connection manager for testing."""
        manager = ConnectionManager()
        handler = WebSocketHandler(manager)
        return handler, manager

    @pytest.mark.asyncio
    async def test_broadcast_agent_joined_event(self, setup_handler):
        """Test broadcasting agent_joined event."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        agent_id = str(uuid4())
        participant_name = "@agent-001"

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_agent_joined(meeting_id, agent_id, participant_name)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "agent_joined"
        assert event["meeting_id"] == str(meeting_id)
        assert event["agent_id"] == agent_id
        assert "timestamp" in event
        assert event["data"]["participant_name"] == participant_name

    @pytest.mark.asyncio
    async def test_broadcast_opinion_presented_event(self, setup_handler):
        """Test broadcasting opinion_presented event."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        agent_id = str(uuid4())
        opinion = "I think we should use PostgreSQL"

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_opinion_presented(meeting_id, agent_id, opinion, round_number=1)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "opinion_presented"
        assert event["agent_id"] == agent_id
        assert event["data"]["opinion"] == opinion
        assert event["data"]["round_number"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_consensus_reached_event(self, setup_handler):
        """Test broadcasting consensus_reached event."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        consensus_option = "PostgreSQL"
        votes = {
            "agent-001": "PostgreSQL",
            "agent-002": "PostgreSQL",
            "agent-003": "PostgreSQL",
        }

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_consensus_reached(meeting_id, consensus_option, votes)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "consensus_reached"
        assert event["data"]["consensus_option"] == consensus_option
        assert event["data"]["votes"] == votes

    @pytest.mark.asyncio
    async def test_broadcast_round_started_event(self, setup_handler):
        """Test broadcasting round_started event."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        round_number = 2
        topic = "Database Selection"

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_round_started(meeting_id, round_number, topic)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "round_started"
        assert event["data"]["round_number"] == round_number
        assert event["data"]["topic"] == topic

    @pytest.mark.asyncio
    async def test_broadcast_round_completed_event(self, setup_handler):
        """Test broadcasting round_completed event."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        round_number = 1
        consensus_reached = True
        consensus_option = "PostgreSQL"

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_round_completed(
            meeting_id, round_number, consensus_reached, consensus_option
        )

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "round_completed"
        assert event["data"]["round_number"] == round_number
        assert event["data"]["consensus_reached"] is True
        assert event["data"]["consensus_option"] == consensus_option

    @pytest.mark.asyncio
    async def test_broadcast_round_completed_no_consensus(self, setup_handler):
        """Test broadcasting round_completed event when no consensus."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        round_number = 2

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event without consensus
        await handler.broadcast_round_completed(meeting_id, round_number, consensus_reached=False)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "round_completed"
        assert event["data"]["consensus_reached"] is False
        assert event["data"]["consensus_option"] is None

    @pytest.mark.asyncio
    async def test_broadcast_discussion_paused_event(self, setup_handler):
        """Test broadcasting discussion_paused event."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        reason = "Waiting for participant"

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_discussion_paused(meeting_id, reason)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "discussion_paused"
        assert event["data"]["reason"] == reason

    @pytest.mark.asyncio
    async def test_broadcast_discussion_resumed_event(self, setup_handler):
        """Test broadcasting discussion_resumed event."""
        handler, manager = setup_handler
        meeting_id = uuid4()

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast event
        await handler.broadcast_discussion_resumed(meeting_id)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "discussion_resumed"


@pytest.mark.integration
class TestMeetingEvent:
    """Tests for MeetingEvent dataclass."""

    def test_meeting_event_to_dict(self):
        """Test converting MeetingEvent to dictionary."""
        event = MeetingEvent(
            event_type=MessageType.AGENT_JOINED,
            meeting_id=uuid4(),
            agent_id="agent-001",
            data={"participant_name": "@agent-001"},
        )

        event_dict = event.to_dict()

        assert event_dict["type"] == "agent_joined"
        assert "meeting_id" in event_dict
        assert "timestamp" in event_dict
        assert event_dict["agent_id"] == "agent-001"
        assert event_dict["data"]["participant_name"] == "@agent-001"

    def test_meeting_event_all_message_types(self):
        """Test that all message types can be used in events."""
        meeting_id = uuid4()

        for msg_type in MessageType:
            event = MeetingEvent(
                event_type=msg_type,
                meeting_id=meeting_id,
            )
            event_dict = event.to_dict()
            assert event_dict["type"] == msg_type.value


@pytest.mark.integration
class TestReconnectionHandling:
    """Tests for reconnection handling."""

    @pytest.fixture
    def setup_handler(self):
        """Set up handler and connection manager for testing."""
        manager = ConnectionManager()
        handler = WebSocketHandler(manager)
        return handler, manager

    @pytest.mark.asyncio
    async def test_handle_reconnect_success(self, setup_handler):
        """Test successful reconnection handling."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        agent_id = str(uuid4())

        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()

        # Add a participant to the meeting first
        mock_agent = Agent(
            id=agent_id,
            nickname="test-agent",
            api_key="test-key",
        )
        await manager.connect(mock_websocket, meeting_id, mock_agent)

        # Handle reconnect
        success = await handler.handle_reconnect(mock_websocket, meeting_id, agent_id)

        # Should succeed
        assert success is True

        # State sync message should be sent
        mock_websocket.send_json.assert_called()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "state_sync"

    @pytest.mark.asyncio
    async def test_handle_reconnect_no_meeting(self, setup_handler):
        """Test reconnection when meeting doesn't exist."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        agent_id = str(uuid4())

        # Mock WebSocket
        mock_websocket = MagicMock()

        # Try to reconnect to non-existent meeting
        success = await handler.handle_reconnect(mock_websocket, meeting_id, agent_id)

        # Should fail
        assert success is False

    @pytest.mark.asyncio
    async def test_handle_reconnect_with_sequence(self, setup_handler):
        """Test reconnection with sequence number."""
        handler, manager = setup_handler
        meeting_id = uuid4()
        agent_id = str(uuid4())
        last_sequence = 42

        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()

        # Add a participant
        mock_agent = Agent(
            id=agent_id,
            nickname="test-agent",
            api_key="test-key",
        )
        await manager.connect(mock_websocket, meeting_id, mock_agent)

        # Handle reconnect with sequence
        success = await handler.handle_reconnect(
            mock_websocket, meeting_id, agent_id, last_sequence
        )

        # Should succeed
        assert success is True

        # State sync should include sequence number
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["data"]["last_sequence"] == last_sequence


@pytest.mark.integration
class TestStateSynchronization:
    """Tests for state synchronization."""

    @pytest.fixture
    def setup_handler(self):
        """Set up handler and connection manager for testing."""
        manager = ConnectionManager()
        handler = WebSocketHandler(manager)
        return handler, manager

    @pytest.mark.asyncio
    async def test_send_state_sync(self, setup_handler):
        """Test sending state synchronization message."""
        handler, manager = setup_handler
        meeting_id = uuid4()

        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()

        # Add some participants
        agent1 = Agent(id=str(uuid4()), nickname="agent1", api_key="key1")
        agent2 = Agent(id=str(uuid4()), nickname="agent2", api_key="key2")
        await manager.connect(mock_websocket, meeting_id, agent1)

        # Create another mock connection for agent2
        mock_websocket2 = MagicMock()
        await manager.connect(mock_websocket2, meeting_id, agent2)

        # Send state sync
        await handler._send_state_sync(mock_websocket, meeting_id, since_sequence=0)

        # Verify message was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]

        assert sent_message["type"] == "state_sync"
        assert sent_message["meeting_id"] == str(meeting_id)
        assert "timestamp" in sent_message
        assert "data" in sent_message
        assert sent_message["data"]["connection_count"] >= 1
        assert sent_message["data"]["last_sequence"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_meeting_state(self, setup_handler):
        """Test broadcasting full meeting state."""
        handler, manager = setup_handler
        meeting_id = uuid4()

        # Create discussion state
        from collections import deque

        discussion_state = DiscussionState(
            meeting_id=meeting_id,
            participants=deque(["agent-001", "agent-002", "agent-003"]),
            current_speaker="agent-001",
            current_round=2,
            max_rounds=3,
            consensus_threshold=0.8,
        )

        # Add some rounds
        round1 = RoundState(round_number=1, consensus_reached=False)
        round2 = RoundState(round_number=2, consensus_reached=True, consensus_option="Option A")
        discussion_state.rounds = [round1, round2]

        # Mock broadcast to capture the event
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Broadcast meeting state
        await handler.broadcast_meeting_state(meeting_id, discussion_state)

        # Verify event was broadcast
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "state_sync"
        assert event["data"]["current_round"] == 2
        assert event["data"]["max_rounds"] == 3
        assert event["data"]["current_speaker"] == "agent-001"
        assert event["data"]["participant_count"] == 3
        assert event["data"]["consensus_threshold"] == 0.8


@pytest.mark.integration
class TestEventFlow:
    """Tests for complete event flows during discussions."""

    @pytest.fixture
    def setup_handler(self):
        """Set up handler and connection manager for testing."""
        manager = ConnectionManager()
        handler = WebSocketHandler(manager)
        return handler, manager

    @pytest.mark.asyncio
    async def test_complete_round_event_flow(self, setup_handler):
        """Test the complete flow of events during a discussion round."""
        handler, manager = setup_handler
        meeting_id = uuid4()

        # Mock broadcast to capture all events
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Simulate a complete round flow
        # 1. Round started
        await handler.broadcast_round_started(meeting_id, 1, "Database Selection")

        # 2. Agent joins
        await handler.broadcast_agent_joined(meeting_id, "agent-001", "@agent-001")

        # 3. Opinion presented
        await handler.broadcast_opinion_presented(
            meeting_id, "agent-001", "PostgreSQL", round_number=1
        )

        # 4. Another opinion
        await handler.broadcast_opinion_presented(
            meeting_id, "agent-002", "MongoDB", round_number=1
        )

        # 5. Third opinion
        await handler.broadcast_opinion_presented(
            meeting_id, "agent-003", "PostgreSQL", round_number=1
        )

        # 6. Consensus reached
        votes = {
            "agent-001": "PostgreSQL",
            "agent-002": "PostgreSQL",
            "agent-003": "PostgreSQL",
        }
        await handler.broadcast_consensus_reached(meeting_id, "PostgreSQL", votes)

        # 7. Round completed
        await handler.broadcast_round_completed(
            meeting_id, 1, consensus_reached=True, consensus_option="PostgreSQL"
        )

        # Verify all events were broadcast in order
        assert len(events) == 7
        assert events[0]["type"] == "round_started"
        assert events[1]["type"] == "agent_joined"
        assert events[2]["type"] == "opinion_presented"
        assert events[3]["type"] == "opinion_presented"
        assert events[4]["type"] == "opinion_presented"
        assert events[5]["type"] == "consensus_reached"
        assert events[6]["type"] == "round_completed"

    @pytest.mark.asyncio
    async def test_multi_round_event_flow(self, setup_handler):
        """Test event flow across multiple rounds."""
        handler, manager = setup_handler
        meeting_id = uuid4()

        # Mock broadcast to capture all events
        events = []
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(mid, message):
            events.append(message)

        manager.broadcast_to_meeting = mock_broadcast

        # Round 1: No consensus
        await handler.broadcast_round_started(meeting_id, 1, "Topic 1")
        await handler.broadcast_opinion_presented(meeting_id, "agent-001", "Opinion A", 1)
        await handler.broadcast_round_completed(meeting_id, 1, consensus_reached=False)

        # Pause between rounds
        await handler.broadcast_discussion_paused(meeting_id, "Preparing next round")

        # Resume discussion
        await handler.broadcast_discussion_resumed(meeting_id)

        # Round 2: Consensus
        await handler.broadcast_round_started(meeting_id, 2, "Topic 1 - Round 2")
        await handler.broadcast_opinion_presented(meeting_id, "agent-001", "Opinion B", 2)
        votes = {"agent-001": "Option A", "agent-002": "Option A"}
        await handler.broadcast_consensus_reached(meeting_id, "Option A", votes)
        await handler.broadcast_round_completed(
            meeting_id, 2, consensus_reached=True, consensus_option="Option A"
        )

        # Verify all events
        assert len(events) == 10
        assert events[0]["type"] == "round_started"
        assert events[0]["data"]["round_number"] == 1
        assert events[3]["type"] == "round_completed"
        assert events[3]["data"]["consensus_reached"] is False

        assert events[4]["type"] == "discussion_paused"
        assert events[5]["type"] == "discussion_resumed"

        assert events[6]["type"] == "round_started"
        assert events[6]["data"]["round_number"] == 2
        assert events[9]["type"] == "round_completed"
        assert events[9]["data"]["consensus_reached"] is True
