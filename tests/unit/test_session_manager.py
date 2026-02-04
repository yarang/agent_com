"""
Unit tests for Session Manager component.

Tests session creation, heartbeat monitoring,
message queuing, and disconnection.
"""

from uuid import uuid4

from mcp_broker.models.message import Message
from mcp_broker.models.session import SessionCapabilities
from mcp_broker.session.manager import SessionManager
from mcp_broker.storage.memory import InMemoryStorage


class TestSessionManager:
    """Tests for SessionManager class."""

    async def test_create_session(self) -> None:
        """Test creating a new session."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        assert session.session_id is not None
        assert session.status == "active"
        assert session.capabilities == capabilities

    async def test_create_session_with_id(self) -> None:
        """Test creating session with specific ID."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_id = uuid4()
        session = await manager.create_session(capabilities, session_id=session_id)

        assert session.session_id == session_id

    async def test_get_session(self) -> None:
        """Test getting a session by ID."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        created = await manager.create_session(capabilities)
        retrieved = await manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    async def test_update_heartbeat(self) -> None:
        """Test updating session heartbeat."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)
        original_hb = session.last_heartbeat

        # Small delay to ensure time difference
        import asyncio

        await asyncio.sleep(0.01)

        updated = await manager.update_heartbeat(session.session_id)

        assert updated is not None
        assert updated.last_heartbeat >= original_hb

    async def test_list_sessions(self) -> None:
        """Test listing sessions."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        await manager.create_session(capabilities)
        await manager.create_session(capabilities)

        sessions = await manager.list_sessions()
        assert len(sessions) == 2

    async def test_list_sessions_by_status(self) -> None:
        """Test listing sessions with status filter."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session1 = await manager.create_session(capabilities)
        session2 = await manager.create_session(capabilities)

        # Mark one as stale manually
        session2.status = "stale"
        await storage.save_session(session2)

        active_sessions = await manager.list_sessions(status_filter="active")
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == session1.session_id

    async def test_disconnect_session(self) -> None:
        """Test disconnecting a session."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        result = await manager.disconnect_session(session.session_id)

        assert result is True

    async def test_enqueue_message(self) -> None:
        """Test enqueuing a message."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        message = Message(
            sender_id=uuid4(),
            recipient_id=session.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        result = await manager.enqueue_message(session.session_id, message)

        assert result.success is True
        assert result.queue_size == 1

    async def test_dequeue_messages(self) -> None:
        """Test dequeuing messages."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        message = Message(
            sender_id=uuid4(),
            recipient_id=session.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        await manager.enqueue_message(session.session_id, message)

        messages = await manager.dequeue_messages(session.session_id)

        assert len(messages) == 1
        assert messages[0].payload == {"text": "Hello"}

    async def test_queue_capacity_limit(self) -> None:
        """Test queue capacity is enforced."""
        storage = InMemoryStorage(queue_capacity=2)
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        message = Message(
            sender_id=uuid4(),
            recipient_id=session.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Fill queue
        result1 = await manager.enqueue_message(session.session_id, message)
        result2 = await manager.enqueue_message(session.session_id, message)

        assert result1.success is True
        assert result2.success is True

        # Third message should fail
        result3 = await manager.enqueue_message(session.session_id, message)
        assert result3.success is False
        assert "full" in result3.error_reason or "full" in str(result3.error_reason).lower()

    async def test_check_stale_sessions(self) -> None:
        """Test checking for stale sessions."""
        storage = InMemoryStorage()
        manager = SessionManager(
            storage,
            stale_threshold=1,  # 1 second threshold
        )

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        # Make session stale by setting old heartbeat
        from datetime import UTC, datetime, timedelta

        old_hb = datetime.now(UTC) - timedelta(seconds=35)
        session.last_heartbeat = old_hb
        await storage.save_session(session, session.project_id)

        stale_sessions = await manager.check_stale_sessions()

        assert len(stale_sessions) == 1
        assert stale_sessions[0].session_id == session.session_id
        assert stale_sessions[0].status == "stale"

    async def test_cleanup_expired_sessions(self) -> None:
        """Test cleaning up expired sessions."""
        storage = InMemoryStorage()
        manager = SessionManager(
            storage,
            disconnect_threshold=1,  # 1 second threshold
        )

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        # Make session expired by setting old heartbeat
        from datetime import UTC, datetime, timedelta

        old_hb = datetime.now(UTC) - timedelta(seconds=65)
        session.last_heartbeat = old_hb
        await storage.save_session(session, session.project_id)

        disconnected = await manager.cleanup_expired_sessions()

        assert len(disconnected) == 1
        assert disconnected[0].session_id == session.session_id

    async def test_update_heartbeat_stale_recovery(self) -> None:
        """Test that heartbeat updates recover stale sessions."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        # Mark as stale
        session.status = "stale"
        await storage.save_session(session)

        # Update heartbeat should recover
        updated = await manager.update_heartbeat(session.session_id)

        assert updated is not None
        assert updated.status == "active"

    async def test_dequeue_messages_with_limit(self) -> None:
        """Test dequeuing messages with limit."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = await manager.create_session(capabilities)

        # Enqueue multiple messages
        for i in range(5):
            message = Message(
                sender_id=uuid4(),
                recipient_id=session.session_id,
                protocol_name="chat",
                protocol_version="1.0.0",
                payload={"text": f"Message {i}"},
            )
            await manager.enqueue_message(session.session_id, message)

        # Dequeue with limit
        messages = await manager.dequeue_messages(session.session_id, limit=3)

        assert len(messages) == 3

    async def test_enqueue_message_nonexistent_session(self) -> None:
        """Test enqueuing to non-existent session."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        message = Message(
            sender_id=uuid4(),
            recipient_id=uuid4(),
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        result = await manager.enqueue_message(uuid4(), message)

        assert result.success is False
        assert "not found" in result.error_reason

    async def test_get_nonexistent_session(self) -> None:
        """Test getting non-existent session."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        result = await manager.get_session(uuid4())

        assert result is None

    async def test_disconnect_nonexistent_session(self) -> None:
        """Test disconnecting non-existent session."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        result = await manager.disconnect_session(uuid4())

        assert result is False

    async def test_duplicate_session_id(self) -> None:
        """Test handling duplicate session IDs."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_id = uuid4()
        session1 = await manager.create_session(capabilities, session_id=session_id)
        session2 = await manager.create_session(capabilities, session_id=session_id)

        # Second create should succeed and first should be disconnected
        assert session2.session_id == session_id

        # First session should be disconnected
        retrieved1 = await manager.get_session(session_id)
        assert retrieved1.status == "active"  # New session is active
