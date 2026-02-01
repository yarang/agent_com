"""
Unit tests for storage layer project namespace isolation.

Tests that projects cannot access each other's data in the
storage layer using the namespace prefix pattern.
"""

import pytest
from uuid import uuid4

from mcp_broker.models.message import Message
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.models.session import Session, SessionCapabilities
from mcp_broker.storage.memory import InMemoryStorage


# Sample schema for testing
SAMPLE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["text"],
}


class TestStorageIsolation:
    """Tests for project namespace isolation in storage layer."""

    async def test_protocol_isolation_by_project(self) -> None:
        """Test protocols are isolated between projects."""
        storage = InMemoryStorage()

        # Register same protocol in different projects
        protocol1 = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        protocol2 = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol1, project_id="project_a")
        await storage.save_protocol(protocol2, project_id="project_b")

        # Each project should see its own protocol
        proto_a = await storage.get_protocol("chat", "1.0.0", project_id="project_a")
        proto_b = await storage.get_protocol("chat", "1.0.0", project_id="project_b")

        assert proto_a is not None
        assert proto_b is not None
        assert proto_a == protocol1
        assert proto_b == protocol2

        # Different version in same project
        protocol_v2 = ProtocolDefinition(
            name="chat",
            version="2.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )
        await storage.save_protocol(protocol_v2, project_id="project_a")

        # List protocols in project_a should have 2 versions
        protos_a = await storage.list_protocols(name="chat", project_id="project_a")
        assert len(protos_a) == 2

        # List protocols in project_b should have 1 version
        protos_b = await storage.list_protocols(name="chat", project_id="project_b")
        assert len(protos_b) == 1

    async def test_protocol_cross_project_access_blocked(self) -> None:
        """Test project cannot access another project's protocol."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="secret",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol, project_id="project_a")

        # Project B should not see Project A's protocol
        proto = await storage.get_protocol("secret", "1.0.0", project_id="project_b")
        assert proto is None

        # List in project B should be empty
        protos = await storage.list_protocols(project_id="project_b")
        assert len(protos) == 0

    async def test_protocol_delete_isolated(self) -> None:
        """Test deleting protocol only affects one project."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol, project_id="project_a")
        await storage.save_protocol(protocol, project_id="project_b")

        # Delete from project A
        result = await storage.delete_protocol("chat", "1.0.0", project_id="project_a")
        assert result is True

        # Project A should not have protocol
        proto_a = await storage.get_protocol("chat", "1.0.0", project_id="project_a")
        assert proto_a is None

        # Project B should still have protocol
        proto_b = await storage.get_protocol("chat", "1.0.0", project_id="project_b")
        assert proto_b is not None

    async def test_protocol_duplicate_same_project(self) -> None:
        """Test duplicate protocol in same project is rejected."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol, project_id="project_a")

        # Same protocol in same project should fail
        with pytest.raises(ValueError, match="already exists"):
            await storage.save_protocol(protocol, project_id="project_a")

    async def test_protocol_duplicate_different_project(self) -> None:
        """Test duplicate protocol in different project is allowed."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol, project_id="project_a")

        # Same protocol in different project should succeed
        await storage.save_protocol(protocol, project_id="project_b")

        # Both should exist
        proto_a = await storage.get_protocol("chat", "1.0.0", project_id="project_a")
        proto_b = await storage.get_protocol("chat", "1.0.0", project_id="project_b")

        assert proto_a is not None
        assert proto_b is not None

    async def test_session_isolation_by_project(self) -> None:
        """Test sessions are isolated between projects."""
        storage = InMemoryStorage()

        session_id = uuid4()
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = Session(session_id=session_id, capabilities=caps)

        # Save session for project A
        await storage.save_session(session, project_id="project_a")

        # Project A should see session
        sess_a = await storage.get_session(session_id, project_id="project_a")
        assert sess_a is not None
        assert sess_a.session_id == session_id

        # Project B should not see session
        sess_b = await storage.get_session(session_id, project_id="project_b")
        assert sess_b is None

    async def test_session_list_isolated(self) -> None:
        """Test listing sessions is isolated by project."""
        storage = InMemoryStorage()

        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session1 = Session(session_id=uuid4(), capabilities=caps, status="active")
        session2 = Session(session_id=uuid4(), capabilities=caps, status="active")

        await storage.save_session(session1, project_id="project_a")
        await storage.save_session(session2, project_id="project_b")

        # Each project should only see its own sessions
        sessions_a = await storage.list_sessions(project_id="project_a")
        sessions_b = await storage.list_sessions(project_id="project_b")

        assert len(sessions_a) == 1
        assert len(sessions_b) == 1
        assert sessions_a[0].session_id == session1.session_id
        assert sessions_b[0].session_id == session2.session_id

    async def test_session_delete_isolated(self) -> None:
        """Test deleting session only affects one project."""
        storage = InMemoryStorage()

        session_id = uuid4()
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = Session(session_id=session_id, capabilities=caps)

        await storage.save_session(session, project_id="project_a")
        await storage.save_session(session, project_id="project_b")

        # Delete from project A
        result = await storage.delete_session(session_id, project_id="project_a")
        assert result is True

        # Project A should not have session
        sess_a = await storage.get_session(session_id, project_id="project_a")
        assert sess_a is None

        # Project B should still have session
        sess_b = await storage.get_session(session_id, project_id="project_b")
        assert sess_b is not None

    async def test_message_queue_isolation(self) -> None:
        """Test message queues are isolated between projects."""
        storage = InMemoryStorage()

        session_id = uuid4()
        sender_id = uuid4()

        message = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Enqueue for project A
        await storage.enqueue_message(session_id, message, project_id="project_a")

        # Project A should have message
        queue_size_a = await storage.get_queue_size(session_id, project_id="project_a")
        assert queue_size_a == 1

        # Project B should not have message
        queue_size_b = await storage.get_queue_size(session_id, project_id="project_b")
        assert queue_size_b == 0

    async def test_message_dequeue_isolated(self) -> None:
        """Test dequeuing messages is isolated by project."""
        storage = InMemoryStorage()

        session_id = uuid4()
        sender_id = uuid4()

        message1 = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"project": "a"},
        )

        message2 = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"project": "b"},
        )

        # Enqueue for both projects
        await storage.enqueue_message(session_id, message1, project_id="project_a")
        await storage.enqueue_message(session_id, message2, project_id="project_b")

        # Each project should dequeue its own message
        messages_a = await storage.dequeue_messages(session_id, project_id="project_a")
        messages_b = await storage.dequeue_messages(session_id, project_id="project_b")

        assert len(messages_a) == 1
        assert len(messages_b) == 1
        assert messages_a[0].payload["project"] == "a"
        assert messages_b[0].payload["project"] == "b"

    async def test_message_clear_queue_isolated(self) -> None:
        """Test clearing queue only affects one project."""
        storage = InMemoryStorage()

        session_id = uuid4()
        sender_id = uuid4()

        message = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Enqueue for both projects
        await storage.enqueue_message(session_id, message, project_id="project_a")
        await storage.enqueue_message(session_id, message, project_id="project_b")

        # Clear queue for project A
        cleared = await storage.clear_queue(session_id, project_id="project_a")
        assert cleared == 1

        # Project A should have empty queue
        queue_size_a = await storage.get_queue_size(session_id, project_id="project_a")
        assert queue_size_a == 0

        # Project B should still have message
        queue_size_b = await storage.get_queue_size(session_id, project_id="project_b")
        assert queue_size_b == 1

    async def test_same_session_id_different_projects(self) -> None:
        """Test same session ID can exist in different projects."""
        storage = InMemoryStorage()

        session_id = uuid4()
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_a = Session(session_id=session_id, capabilities=caps, status="active")
        session_b = Session(session_id=session_id, capabilities=caps, status="stale")

        # Same session ID, different projects
        await storage.save_session(session_a, project_id="project_a")
        await storage.save_session(session_b, project_id="project_b")

        # Each project should see its own session
        retrieved_a = await storage.get_session(session_id, project_id="project_a")
        retrieved_b = await storage.get_session(session_id, project_id="project_b")

        assert retrieved_a is not None
        assert retrieved_b is not None
        assert retrieved_a.status == "active"
        assert retrieved_b.status == "stale"

    async def test_default_project_backward_compatibility(self) -> None:
        """Test default project ensures backward compatibility."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        # Save without specifying project_id
        await storage.save_protocol(protocol)

        # Should be retrievable without project_id
        proto = await storage.get_protocol("chat", "1.0.0")
        assert proto is not None

        # Should also be retrievable with default project_id
        proto_default = await storage.get_protocol("chat", "1.0.0", project_id="default")
        assert proto_default is not None

    async def test_list_all_protocols_across_projects(self) -> None:
        """Test listing protocols across multiple projects."""
        storage = InMemoryStorage()

        protocol1 = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        protocol2 = ProtocolDefinition(
            name="file",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol1, project_id="project_a")
        await storage.save_protocol(protocol2, project_id="project_b")

        # List all in project_a
        protos_a = await storage.list_protocols(project_id="project_a")
        assert len(protos_a) == 1
        assert protos_a[0].name == "chat"

        # List all in project_b
        protos_b = await storage.list_protocols(project_id="project_b")
        assert len(protos_b) == 1
        assert protos_b[0].name == "file"

        # List all without project_id (default project)
        protos_default = await storage.list_protocols()
        assert len(protos_default) == 0

    async def test_list_all_sessions_across_projects(self) -> None:
        """Test listing sessions across multiple projects."""
        storage = InMemoryStorage()

        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session1 = Session(session_id=uuid4(), capabilities=caps)
        session2 = Session(session_id=uuid4(), capabilities=caps)
        session3 = Session(session_id=uuid4(), capabilities=caps)

        await storage.save_session(session1, project_id="project_a")
        await storage.save_session(session2, project_id="project_a")
        await storage.save_session(session3, project_id="project_b")

        # List in project_a
        sessions_a = await storage.list_sessions(project_id="project_a")
        assert len(sessions_a) == 2

        # List in project_b
        sessions_b = await storage.list_sessions(project_id="project_b")
        assert len(sessions_b) == 1

        # List without project_id (default project)
        sessions_default = await storage.list_sessions()
        assert len(sessions_default) == 0
