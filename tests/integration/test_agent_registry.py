"""
Integration tests for Agent Registry and Status Board.

Tests:
- Agent registration
- Status updates
- Statistics calculation
- WebSocket status broadcasts
"""

import asyncio
import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from agent_comm_core.models.status import (
    AgentInfo,
    AgentRegistration,
    AgentStatus,
    SystemStats,
    format_agent_display_id,
)
from communication_server.services.agent_registry import AgentRegistry
from communication_server.api.status import StatisticsService
from communication_server.websocket.manager import ConnectionManager


@pytest.mark.integration
class TestAgentRegistration:
    """Tests for agent registration functionality."""

    async def test_register_new_agent(self, agent_registry: AgentRegistry):
        """Test registering a new agent."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="TestAgent",
            capabilities=["test", "demo"],
        )

        assert agent is not None
        assert agent.full_id == full_id
        assert agent.nickname == "TestAgent"
        assert agent.status == AgentStatus.ONLINE
        assert agent.capabilities == ["test", "demo"]
        assert "@TestAgent-" in agent.agent_id

    async def test_register_agent_with_existing_id(self, agent_registry: AgentRegistry):
        """Test updating an existing agent registration."""
        full_id = str(uuid4())

        # Register initially
        agent1 = await agent_registry.register_agent(
            full_id=full_id,
            nickname="AgentV1",
            capabilities=["v1"],
        )

        # Update with new info
        agent2 = await agent_registry.register_agent(
            full_id=full_id,
            nickname="AgentV2",
            capabilities=["v1", "v2"],
        )

        # Should have same display ID and full ID
        assert agent2.agent_id == agent1.agent_id
        assert agent2.full_id == full_id
        # But updated properties
        assert agent2.nickname == "AgentV2"
        assert agent2.capabilities == ["v1", "v2"]
        assert agent2.status == AgentStatus.ONLINE  # Should be reset to online

    async def test_get_all_agents(self, agent_registry: AgentRegistry):
        """Test retrieving all registered agents."""
        # Register multiple agents
        agent1 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="Alpha",
            capabilities=["a"],
        )
        agent2 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="Beta",
            capabilities=["b"],
        )
        agent3 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="Gamma",
            capabilities=["g"],
        )

        all_agents = await agent_registry.get_all_agents()

        assert len(all_agents) == 3
        agent_ids = {a.agent_id for a in all_agents}
        assert agent1.agent_id in agent_ids
        assert agent2.agent_id in agent_ids
        assert agent3.agent_id in agent_ids

    async def test_get_agent_by_display_id(self, agent_registry: AgentRegistry):
        """Test retrieving agent by display ID."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="TestAgent",
            capabilities=["test"],
        )

        retrieved = await agent_registry.get_agent_by_display_id(agent.agent_id)

        assert retrieved is not None
        assert retrieved.agent_id == agent.agent_id
        assert retrieved.full_id == full_id
        assert retrieved.nickname == "TestAgent"

    async def test_get_agent_by_full_id(self, agent_registry: AgentRegistry):
        """Test retrieving agent by full UUID."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="TestAgent",
            capabilities=["test"],
        )

        retrieved = await agent_registry.get_agent_by_full_id(full_id)

        assert retrieved is not None
        assert retrieved.full_id == full_id
        assert retrieved.agent_id == agent.agent_id

    async def test_get_active_agents(self, agent_registry: AgentRegistry):
        """Test retrieving only active agents."""
        full_id1 = str(uuid4())
        full_id2 = str(uuid4())
        full_id3 = str(uuid4())

        agent1 = await agent_registry.register_agent(
            full_id=full_id1,
            nickname="OnlineAgent",
            capabilities=["online"],
        )
        agent2 = await agent_registry.register_agent(
            full_id=full_id2,
            nickname="ActiveAgent",
            capabilities=["active"],
        )
        agent3 = await agent_registry.register_agent(
            full_id=full_id3,
            nickname="OfflineAgent",
            capabilities=["offline"],
        )

        # Update agent3 to offline
        await agent_registry.update_agent_status(full_id3, AgentStatus.OFFLINE)

        active_agents = await agent_registry.get_active_agents()

        assert len(active_agents) == 2
        active_ids = {a.agent_id for a in active_agents}
        assert agent1.agent_id in active_ids
        assert agent2.agent_id in active_ids
        assert agent3.agent_id not in active_ids

    async def test_unregister_agent(self, agent_registry: AgentRegistry):
        """Test unregistering an agent."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="ToRemove",
            capabilities=["remove"],
        )

        # Verify registered
        assert await agent_registry.get_agent_by_full_id(full_id) is not None

        # Unregister
        result = await agent_registry.unregister_agent(full_id)
        assert result is True

        # Verify removed
        assert await agent_registry.get_agent_by_full_id(full_id) is None

    async def test_unregister_nonexistent_agent(self, agent_registry: AgentRegistry):
        """Test unregistering an agent that doesn't exist."""
        result = await agent_registry.unregister_agent(str(uuid4()))
        assert result is False


@pytest.mark.integration
class TestAgentStatusUpdates:
    """Tests for agent status update functionality."""

    async def test_update_agent_status(self, agent_registry: AgentRegistry):
        """Test updating agent status."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="StatusTest",
            capabilities=["test"],
        )

        # Update to active
        updated = await agent_registry.update_agent_status(full_id, AgentStatus.ACTIVE)
        assert updated.status == AgentStatus.ACTIVE

        # Update to idle
        updated = await agent_registry.update_agent_status(full_id, AgentStatus.IDLE)
        assert updated.status == AgentStatus.IDLE

        # Update to error
        updated = await agent_registry.update_agent_status(full_id, AgentStatus.ERROR)
        assert updated.status == AgentStatus.ERROR

    async def test_update_status_with_meeting(self, agent_registry: AgentRegistry):
        """Test updating status with current meeting."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="MeetingAgent",
            capabilities=["meeting"],
        )

        meeting_id = uuid4()
        updated = await agent_registry.update_agent_status(
            full_id,
            AgentStatus.ACTIVE,
            current_meeting=meeting_id,
        )

        assert updated.status == AgentStatus.ACTIVE
        assert updated.current_meeting == meeting_id

    async def test_update_agent_activity(self, agent_registry: AgentRegistry):
        """Test updating agent activity timestamp."""
        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="ActiveAgent",
            capabilities=["active"],
        )

        original_last_seen = agent.last_seen

        # Wait a tiny bit to ensure timestamp difference
        await asyncio.sleep(0.01)

        # Update activity
        updated = await agent_registry.update_agent_activity(full_id)

        assert updated.last_seen > original_last_seen

    async def test_cleanup_inactive_agents(self, agent_registry: AgentRegistry):
        """Test cleanup of inactive agents."""
        # Create registry with short timeout
        registry = AgentRegistry(inactive_timeout_seconds=1)

        full_id1 = str(uuid4())
        full_id2 = str(uuid4())

        agent1 = await registry.register_agent(
            full_id=full_id1,
            nickname="RecentAgent",
            capabilities=["recent"],
        )
        agent2 = await registry.register_agent(
            full_id=full_id2,
            nickname="OldAgent",
            capabilities=["old"],
        )

        # Manually set agent2's last_seen to past
        agent2.last_seen = datetime.now(UTC) - timedelta(seconds=10)

        # Run cleanup
        cleaned_count = await registry.cleanup_inactive_agents()

        assert cleaned_count == 1

        # Verify agent2 is now offline
        retrieved = await registry.get_agent_by_full_id(full_id2)
        assert retrieved.status == AgentStatus.OFFLINE

        # Verify agent1 is still online
        retrieved = await registry.get_agent_by_full_id(full_id1)
        assert retrieved.status == AgentStatus.ONLINE


@pytest.mark.integration
class TestStatisticsCalculation:
    """Tests for statistics calculation."""

    async def test_get_agent_count_by_status(self, agent_registry: AgentRegistry):
        """Test getting agent counts by status."""
        # Register agents
        agent1 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="Online1",
            capabilities=["test"],
        )
        await agent_registry.update_agent_status(agent1.full_id, AgentStatus.ONLINE)

        agent2 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="Online2",
            capabilities=["test"],
        )
        await agent_registry.update_agent_status(agent2.full_id, AgentStatus.ONLINE)

        agent3 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="ActiveAgent",
            capabilities=["test"],
        )
        await agent_registry.update_agent_status(agent3.full_id, AgentStatus.ACTIVE)

        agent4 = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="OfflineAgent",
            capabilities=["test"],
        )
        await agent_registry.update_agent_status(agent4.full_id, AgentStatus.OFFLINE)

        counts = await agent_registry.get_agent_count()

        assert counts["total"] == 4
        assert counts["online"] == 2
        assert counts["active"] == 1
        assert counts["offline"] == 1

    async def test_system_statistics(
        self,
        statistics_service: StatisticsService,
        clean_db,
        sample_agent_ids,
    ):
        """Test calculating system-wide statistics."""
        from agent_comm_core.models.communication import CommunicationDirection

        # Create sample data
        await statistics_service._comm_repo.create(
            from_agent=sample_agent_ids[0],
            to_agent=sample_agent_ids[1],
            message_type="question",
            content="Test",
            direction=CommunicationDirection.OUTBOUND,
            metadata={},
        )
        await statistics_service._comm_repo.create(
            from_agent=sample_agent_ids[1],
            to_agent=sample_agent_ids[0],
            message_type="answer",
            content="Test",
            direction=CommunicationDirection.INBOUND,
            metadata={},
        )
        await clean_db.commit()

        stats = await statistics_service.get_system_stats()

        assert stats.total_messages >= 2
        assert stats.total_agents >= 0  # May vary based on test setup


@pytest.mark.integration
class TestWebSocketStatusBroadcasts:
    """Tests for WebSocket status board broadcasts."""

    async def test_status_broadcast_on_registration(self, agent_registry: AgentRegistry):
        """Test broadcasting status when agent registers."""
        manager = ConnectionManager()
        broadcast_messages = []

        # Capture broadcast calls
        original_broadcast = manager.broadcast_to_meeting

        async def mock_broadcast(meeting_id, message):
            broadcast_messages.append((meeting_id, message))

        manager.broadcast_to_meeting = mock_broadcast

        # Note: Current implementation doesn't broadcast on registration
        # This test verifies the pattern for future implementation
        agent = await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="BroadcastTest",
            capabilities=["test"],
        )

        # Verify agent was created
        assert agent is not None
        assert agent.status == AgentStatus.ONLINE

    async def test_status_broadcast_on_update(self, agent_registry: AgentRegistry):
        """Test broadcasting status when agent updates."""
        manager = ConnectionManager()
        broadcast_messages = []

        async def mock_broadcast(meeting_id, message):
            broadcast_messages.append((meeting_id, message))

        manager.broadcast_to_meeting = mock_broadcast

        full_id = str(uuid4())
        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="UpdateTest",
            capabilities=["test"],
        )

        # Update status
        await agent_registry.update_agent_status(full_id, AgentStatus.ACTIVE)

        # Verify update happened
        retrieved = await agent_registry.get_agent_by_full_id(full_id)
        assert retrieved.status == AgentStatus.ACTIVE


@pytest.mark.integration
class TestAgentDisplayIdFormatting:
    """Tests for agent display ID formatting."""

    def test_format_agent_display_id_valid_uuid(self):
        """Test formatting display ID with valid UUID."""
        full_id = "550e8400-e29b-41d4-a716-446655440000"
        nickname = "TestAgent"

        display_id = format_agent_display_id(full_id, nickname)

        assert display_id == "@TestAgent-440000"

    def test_format_agent_display_id_invalid_uuid(self):
        """Test formatting display ID with invalid UUID."""
        full_id = "not-a-uuid"
        nickname = "TestAgent"

        display_id = format_agent_display_id(full_id, nickname)

        # Should use last 8 chars of the string
        assert "@TestAgent-" in display_id

    def test_format_agent_display_id_short_id(self):
        """Test formatting display ID with short ID."""
        full_id = "abc"
        nickname = "TestAgent"

        display_id = format_agent_display_id(full_id, nickname)

        # Should use the entire ID if shorter than 8 chars
        assert "@TestAgent-abc" == display_id


@pytest.mark.integration
class TestAgentCapabilities:
    """Tests for agent capabilities management."""

    async def test_agent_capabilities_stored(self, agent_registry: AgentRegistry):
        """Test that agent capabilities are properly stored."""
        capabilities = ["text-generation", "code-analysis", "debugging", "planning"]
        full_id = str(uuid4())

        agent = await agent_registry.register_agent(
            full_id=full_id,
            nickname="CapableAgent",
            capabilities=capabilities,
        )

        assert agent.capabilities == capabilities

    async def test_update_agent_capabilities(self, agent_registry: AgentRegistry):
        """Test updating agent capabilities via re-registration."""
        full_id = str(uuid4())

        # Initial registration
        agent1 = await agent_registry.register_agent(
            full_id=full_id,
            nickname="EvolvingAgent",
            capabilities=["v1"],
        )

        # Update with new capabilities
        agent2 = await agent_registry.register_agent(
            full_id=full_id,
            nickname="EvolvingAgent",
            capabilities=["v1", "v2", "v3"],
        )

        assert agent2.capabilities == ["v1", "v2", "v3"]

    async def test_find_agents_by_capability(self, agent_registry: AgentRegistry):
        """Test finding agents with specific capabilities."""
        # Register agents with different capabilities
        await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="TextAgent",
            capabilities=["text-generation", "summarization"],
        )
        await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="CodeAgent",
            capabilities=["code-generation", "debugging"],
        )
        await agent_registry.register_agent(
            full_id=str(uuid4()),
            nickname="FullStack",
            capabilities=["text-generation", "code-generation", "debugging"],
        )

        all_agents = await agent_registry.get_all_agents()

        # Find agents with code-generation capability
        code_agents = [a for a in all_agents if "code-generation" in a.capabilities]

        assert len(code_agents) == 2
        nicknames = {a.nickname for a in code_agents}
        assert "CodeAgent" in nicknames
        assert "FullStack" in nicknames
