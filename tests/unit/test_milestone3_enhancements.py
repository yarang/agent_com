"""
Unit tests for Milestone 3 Component Enhancements.

Tests for protocol sharing, project-scoped session management,
per-project message statistics, and project-scoped capability negotiation.
"""

from uuid import uuid4

import pytest

from mcp_broker.models.message import Message
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.models.session import Session, SessionCapabilities
from mcp_broker.negotiation.negotiator import (
    CapabilityNegotiator,
)
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.routing.router import MessageRouter, MessageStatistics
from mcp_broker.session.manager import SessionManager
from mcp_broker.storage.memory import InMemoryStorage


class TestProtocolSharing:
    """Tests for protocol sharing between projects."""

    async def test_share_protocol_with_another_project(self) -> None:
        """Test sharing a protocol with another project."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Register protocol in project_a
        protocol = ProtocolDefinition(
            name="shared_proto",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            capabilities=["point_to_point"],
        )
        await registry.register(protocol, project_id="project_a")

        # Share with project_b
        result = await registry.share_protocol("shared_proto", "1.0.0", "project_a", "project_b")

        assert result is True

    async def test_discover_shared_protocols(self) -> None:
        """Test discovering shared protocols."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Register protocol in project_a
        protocol = ProtocolDefinition(
            name="shared_proto",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            capabilities=["point_to_point"],
        )
        await registry.register(protocol, project_id="project_a")

        # Share with project_b
        await registry.share_protocol("shared_proto", "1.0.0", "project_a", "project_b")

        # Discover with include_shared
        protocols_b = await registry.discover(project_id="project_b", include_shared=True)

        assert len(protocols_b) == 1
        assert protocols_b[0].name == "shared_proto"

    async def test_discover_without_shared_protocols(self) -> None:
        """Test discovery excludes shared protocols by default."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Register protocol in project_a
        protocol = ProtocolDefinition(
            name="shared_proto",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            capabilities=["point_to_point"],
        )
        await registry.register(protocol, project_id="project_a")

        # Share with project_b
        await registry.share_protocol("shared_proto", "1.0.0", "project_a", "project_b")

        # Discover without include_shared
        protocols_b = await registry.discover(project_id="project_b", include_shared=False)

        # Should not include shared protocol
        assert len(protocols_b) == 0

    async def test_unshare_protocol(self) -> None:
        """Test unsharing a protocol."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Register and share
        protocol = ProtocolDefinition(
            name="shared_proto",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            capabilities=["point_to_point"],
        )
        await registry.register(protocol, project_id="project_a")
        await registry.share_protocol("shared_proto", "1.0.0", "project_a", "project_b")

        # Unshare
        result = await registry.unshare_protocol("shared_proto", "1.0.0", "project_a", "project_b")

        assert result is True

        # Verify it's no longer shared
        protocols_b = await registry.discover(project_id="project_b", include_shared=True)
        assert len(protocols_b) == 0

    async def test_list_shared_protocols(self) -> None:
        """Test listing shared protocols for a project."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Register multiple protocols in project_a
        for i in range(3):
            protocol = ProtocolDefinition(
                name=f"proto_{i}",
                version="1.0.0",
                message_schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                },
                capabilities=["point_to_point"],
            )
            await registry.register(protocol, project_id="project_a")
            await registry.share_protocol(f"proto_{i}", "1.0.0", "project_a", "project_b")

        # List shared protocols
        shared = await registry.list_shared_protocols("project_b")

        assert len(shared) == 3
        assert all(s["source_project"] == "project_a" for s in shared)

    async def test_share_within_same_project_raises_error(self) -> None:
        """Test that sharing within same project raises error."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocol = ProtocolDefinition(
            name="test_proto",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            capabilities=["point_to_point"],
        )
        await registry.register(protocol, project_id="project_a")

        # Should raise ValueError
        with pytest.raises(ValueError, match="Cannot share protocol within the same project"):
            await registry.share_protocol("test_proto", "1.0.0", "project_a", "project_a")


class TestProjectScopedSessionManagement:
    """Tests for project-scoped session management."""

    async def test_check_stale_sessions_scoped_to_project(self) -> None:
        """Test stale session checking is project-scoped."""
        storage = InMemoryStorage()
        manager = SessionManager(
            storage,
            stale_threshold=1,  # 1 second threshold
        )

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create sessions in different projects
        session_a = await manager.create_session(capabilities, project_id="project_a")
        session_b = await manager.create_session(capabilities, project_id="project_b")

        # Make session_a stale
        from datetime import UTC, datetime, timedelta

        old_hb = datetime.now(UTC) - timedelta(seconds=35)
        session_a.last_heartbeat = old_hb
        await storage.save_session(session_a, session_a.project_id)

        # Check only project_a
        stale = await manager.check_stale_sessions(project_id="project_a")

        assert len(stale) == 1
        assert stale[0].session_id == session_a.session_id

    async def test_cleanup_expired_sessions_scoped_to_project(self) -> None:
        """Test expired session cleanup is project-scoped."""
        storage = InMemoryStorage()
        manager = SessionManager(
            storage,
            disconnect_threshold=1,  # 1 second threshold
        )

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create sessions in different projects
        session_a = await manager.create_session(capabilities, project_id="project_a")
        session_b = await manager.create_session(capabilities, project_id="project_b")

        # Make session_a expired
        from datetime import UTC, datetime, timedelta

        old_hb = datetime.now(UTC) - timedelta(seconds=65)
        session_a.last_heartbeat = old_hb
        await storage.save_session(session_a, session_a.project_id)

        # Cleanup only project_a
        disconnected = await manager.cleanup_expired_sessions(project_id="project_a")

        assert len(disconnected) == 1
        assert disconnected[0].session_id == session_a.session_id


class TestPerProjectMessageStatistics:
    """Tests for per-project message statistics."""

    async def test_message_statistics_tracking(self) -> None:
        """Test message statistics are tracked per project."""
        storage = InMemoryStorage()
        session_manager = SessionManager(storage)
        router = MessageRouter(session_manager, storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create sessions in project_a
        sender = await session_manager.create_session(capabilities, project_id="project_a")
        recipient = await session_manager.create_session(capabilities, project_id="project_a")

        message = Message(
            sender_id=sender.session_id,
            recipient_id=recipient.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Send message
        await router.send_message(
            sender.session_id, recipient.session_id, message, project_id="project_a"
        )

        # Check statistics
        stats = router.get_project_statistics("project_a")
        assert stats is not None
        assert stats["total_sent"] == 1
        assert stats["total_delivered"] == 1

    async def test_statistics_isolated_between_projects(self) -> None:
        """Test statistics are isolated between projects."""
        storage = InMemoryStorage()
        session_manager = SessionManager(storage)
        router = MessageRouter(session_manager, storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create sessions in different projects
        sender_a = await session_manager.create_session(capabilities, project_id="project_a")
        recipient_a = await session_manager.create_session(capabilities, project_id="project_a")
        sender_b = await session_manager.create_session(capabilities, project_id="project_b")
        recipient_b = await session_manager.create_session(capabilities, project_id="project_b")

        message = Message(
            sender_id=sender_a.session_id,
            recipient_id=recipient_a.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Send message in project_a
        await router.send_message(
            sender_a.session_id,
            recipient_a.session_id,
            message,
            project_id="project_a",
        )

        # Send message in project_b
        message_b = Message(
            sender_id=sender_b.session_id,
            recipient_id=recipient_b.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )
        await router.send_message(
            sender_b.session_id,
            recipient_b.session_id,
            message_b,
            project_id="project_b",
        )

        # Check statistics are isolated
        stats_a = router.get_project_statistics("project_a")
        stats_b = router.get_project_statistics("project_b")

        assert stats_a["total_sent"] == 1
        assert stats_b["total_sent"] == 1

    async def test_broadcast_statistics(self) -> None:
        """Test broadcast statistics are tracked."""
        storage = InMemoryStorage()
        session_manager = SessionManager(storage)
        router = MessageRouter(session_manager, storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["broadcast"],
        )

        # Create sessions
        sender = await session_manager.create_session(capabilities, project_id="project_a")
        recipient1 = await session_manager.create_session(capabilities, project_id="project_a")
        recipient2 = await session_manager.create_session(capabilities, project_id="project_a")

        message = Message(
            sender_id=sender.session_id,
            recipient_id=None,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Broadcast"},
        )

        # Broadcast
        await router.broadcast_message(sender.session_id, message, project_id="project_a")

        # Check statistics
        stats = router.get_project_statistics("project_a")
        assert stats["total_broadcast"] == 1
        # Should have sent to 2 recipients
        assert stats["total_sent"] >= 2

    async def test_get_all_statistics(self) -> None:
        """Test getting statistics for all projects."""
        storage = InMemoryStorage()
        session_manager = SessionManager(storage)
        router = MessageRouter(session_manager, storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create sessions in multiple projects
        for project_id in ["project_a", "project_b", "project_c"]:
            sender = await session_manager.create_session(capabilities, project_id=project_id)
            recipient = await session_manager.create_session(capabilities, project_id=project_id)

            message = Message(
                sender_id=sender.session_id,
                recipient_id=recipient.session_id,
                protocol_name="chat",
                protocol_version="1.0.0",
                payload={"text": "Hello"},
            )

            await router.send_message(
                sender.session_id,
                recipient.session_id,
                message,
                project_id=project_id,
            )

        # Get all statistics
        all_stats = router.get_all_statistics()

        assert len(all_stats) == 3
        assert "project_a" in all_stats
        assert "project_b" in all_stats
        assert "project_c" in all_stats

    async def test_failed_message_statistics(self) -> None:
        """Test failed message statistics are tracked."""
        storage = InMemoryStorage()
        session_manager = SessionManager(storage)
        router = MessageRouter(session_manager, storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        sender = await session_manager.create_session(capabilities, project_id="project_a")

        message = Message(
            sender_id=sender.session_id,
            recipient_id=uuid4(),  # Non-existent recipient
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Send to non-existent recipient
        await router.send_message(
            sender.session_id,
            uuid4(),
            message,
            project_id="project_a",
        )

        # Check failed statistics
        stats = router.get_project_statistics("project_a")
        assert stats["total_failed"] >= 1


class TestProjectScopedCapabilityNegotiation:
    """Tests for project-scoped capability negotiation."""

    async def test_negotiate_rejects_cross_project_by_default(self) -> None:
        """Test negotiation rejects cross-project by default."""
        negotiator = CapabilityNegotiator()

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_a = Session(
            session_id=uuid4(),
            project_id="project_a",
            capabilities=capabilities,
        )
        session_b = Session(
            session_id=uuid4(),
            project_id="project_b",  # Different project
            capabilities=capabilities,
        )

        result = await negotiator.negotiate(session_a, session_b)

        assert result.compatible is False
        assert result.cross_project is True
        assert len(result.incompatibilities) > 0
        assert "cross-project" in result.incompatibilities[0].lower()

    async def test_negotiate_allows_cross_project_when_enabled(self) -> None:
        """Test negotiation allows cross-project when enabled."""
        negotiator = CapabilityNegotiator()

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_a = Session(
            session_id=uuid4(),
            project_id="project_a",
            capabilities=capabilities,
        )
        session_b = Session(
            session_id=uuid4(),
            project_id="project_b",  # Different project
            capabilities=capabilities,
        )

        result = await negotiator.negotiate(session_a, session_b, allow_cross_project=True)

        assert result.compatible is True
        assert result.cross_project is True
        assert "chat" in result.supported_protocols

    async def test_compatibility_matrix_with_cross_project(self) -> None:
        """Test compatibility matrix respects cross-project setting."""
        negotiator = CapabilityNegotiator()

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        sessions = [
            Session(
                session_id=uuid4(),
                project_id="project_a",
                capabilities=capabilities,
            ),
            Session(
                session_id=uuid4(),
                project_id="project_b",
                capabilities=capabilities,
            ),
        ]

        # Without cross-project allowed
        matrix = negotiator.compute_compatibility_matrix(sessions, allow_cross_project=False)

        # Should be incompatible due to cross-project
        assert len(matrix.pairs) == 1
        pair = list(matrix.pairs.values())[0]
        assert pair.compatible is False
        assert pair.cross_project is True

        # With cross-project allowed
        matrix_cross = negotiator.compute_compatibility_matrix(sessions, allow_cross_project=True)

        # Should be compatible
        pair_cross = list(matrix_cross.pairs.values())[0]
        assert pair_cross.compatible is True
        assert pair_cross.cross_project is True

    async def test_compatibility_matrix_project_grouping(self) -> None:
        """Test compatibility matrix groups sessions by project."""
        negotiator = CapabilityNegotiator()

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        sessions = [
            Session(
                session_id=uuid4(),
                project_id="project_a",
                capabilities=capabilities,
            ),
            Session(
                session_id=uuid4(),
                project_id="project_a",
                capabilities=capabilities,
            ),
            Session(
                session_id=uuid4(),
                project_id="project_b",
                capabilities=capabilities,
            ),
        ]

        matrix = negotiator.compute_compatibility_matrix(sessions)

        # Check project grouping
        assert "project_a" in matrix.project_groups
        assert "project_b" in matrix.project_groups
        assert len(matrix.project_groups["project_a"]) == 2
        assert len(matrix.project_groups["project_b"]) == 1

    async def test_negotiate_same_project_succeeds(self) -> None:
        """Test negotiation within same project succeeds."""
        negotiator = CapabilityNegotiator()

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_a = Session(
            session_id=uuid4(),
            project_id="project_a",
            capabilities=capabilities,
        )
        session_b = Session(
            session_id=uuid4(),
            project_id="project_a",  # Same project
            capabilities=capabilities,
        )

        result = await negotiator.negotiate(session_a, session_b)

        assert result.compatible is True
        assert result.cross_project is False


class TestMessageStatistics:
    """Tests for MessageStatistics class."""

    def test_statistics_initialization(self) -> None:
        """Test statistics are initialized correctly."""
        stats = MessageStatistics()

        assert stats.total_sent == 0
        assert stats.total_delivered == 0
        assert stats.total_queued == 0
        assert stats.total_failed == 0
        assert stats.total_broadcast == 0
        assert stats.last_activity is None

    def test_record_sent(self) -> None:
        """Test recording sent messages."""
        stats = MessageStatistics()
        stats.record_sent()

        assert stats.total_sent == 1
        assert stats.last_activity is not None

    def test_record_delivered(self) -> None:
        """Test recording delivered messages."""
        stats = MessageStatistics()
        stats.record_delivered()

        assert stats.total_delivered == 1
        assert stats.last_activity is not None

    def test_record_queued(self) -> None:
        """Test recording queued messages."""
        stats = MessageStatistics()
        stats.record_queued()

        assert stats.total_queued == 1
        assert stats.last_activity is not None

    def test_record_failed(self) -> None:
        """Test recording failed messages."""
        stats = MessageStatistics()
        stats.record_failed()

        assert stats.total_failed == 1
        assert stats.last_activity is not None

    def test_record_broadcast(self) -> None:
        """Test recording broadcast messages."""
        stats = MessageStatistics()
        stats.record_broadcast(5)

        assert stats.total_broadcast == 1
        assert stats.total_sent == 5
        assert stats.last_activity is not None

    def test_to_dict(self) -> None:
        """Test converting statistics to dictionary."""
        stats = MessageStatistics()
        stats.record_sent()
        stats.record_delivered()

        result = stats.to_dict()

        assert result["total_sent"] == 1
        assert result["total_delivered"] == 1
        assert "last_activity" in result
