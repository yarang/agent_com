"""
Unit tests for storage layer components.

Tests the InMemoryStorage implementation for protocol,
session, and message queue operations.
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


class TestInMemoryStorage:
    """Tests for InMemoryStorage class."""

    async def test_protocol_save_and_get(self) -> None:
        """Test saving and retrieving a protocol."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat_message",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol)
        retrieved = await storage.get_protocol("chat_message", "1.0.0")

        assert retrieved is not None
        assert retrieved.name == "chat_message"
        assert retrieved.version == "1.0.0"

    async def test_protocol_duplicate_prevention(self) -> None:
        """Test duplicate protocol is rejected."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat_message",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol)

        with pytest.raises(ValueError, match="already exists"):
            await storage.save_protocol(protocol)

    async def test_protocol_list_all(self) -> None:
        """Test listing all protocols."""
        storage = InMemoryStorage()

        protocol1 = ProtocolDefinition(
            name="chat_message",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        protocol2 = ProtocolDefinition(
            name="file_transfer",
            version="2.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol1)
        await storage.save_protocol(protocol2)

        protocols = await storage.list_protocols()
        assert len(protocols) == 2

    async def test_protocol_list_by_name(self) -> None:
        """Test listing protocols by name."""
        storage = InMemoryStorage()

        protocol = ProtocolDefinition(
            name="chat_message",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol)

        protocols = await storage.list_protocols(name="chat_message")
        assert len(protocols) == 1
        assert protocols[0].name == "chat_message"

    async def test_session_save_and_get(self) -> None:
        """Test saving and retrieving a session."""
        storage = InMemoryStorage()

        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = Session(session_id=uuid4(), capabilities=caps)
        await storage.save_session(session)
        retrieved = await storage.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.status == "active"

    async def test_session_list(self) -> None:
        """Test listing sessions."""
        storage = InMemoryStorage()

        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session1 = Session(session_id=uuid4(), status="active", capabilities=caps)
        session2 = Session(session_id=uuid4(), status="stale", capabilities=caps)

        await storage.save_session(session1)
        await storage.save_session(session2)

        all_sessions = await storage.list_sessions()
        assert len(all_sessions) == 2

    async def test_message_enqueue_and_dequeue(self) -> None:
        """Test enqueuing and dequeuing messages."""
        storage = InMemoryStorage()

        session_id = uuid4()
        message = Message(
            sender_id=uuid4(),
            recipient_id=session_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "test"},
        )

        await storage.enqueue_message(session_id, message)
        queue_size = await storage.get_queue_size(session_id)
        assert queue_size == 1

        messages = await storage.dequeue_messages(session_id, limit=10)
        assert len(messages) == 1
        assert messages[0].message_id == message.message_id

    async def test_message_queue_capacity(self) -> None:
        """Test queue capacity limit."""
        storage = InMemoryStorage(queue_capacity=2)

        session_id = uuid4()
        sender_id = uuid4()

        message1 = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "1"},
        )
        message2 = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "2"},
        )
        message3 = Message(
            sender_id=sender_id,
            recipient_id=session_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "3"},
        )

        await storage.enqueue_message(session_id, message1)
        await storage.enqueue_message(session_id, message2)

        # Third message should fail
        with pytest.raises(ValueError, match="full"):
            await storage.enqueue_message(session_id, message3)

    async def test_message_clear_queue(self) -> None:
        """Test clearing message queue."""
        storage = InMemoryStorage()

        session_id = uuid4()
        message = Message(
            sender_id=uuid4(),
            recipient_id=session_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "test"},
        )

        await storage.enqueue_message(session_id, message)
        assert await storage.get_queue_size(session_id) == 1

        cleared = await storage.clear_queue(session_id)
        assert cleared == 1
        assert await storage.get_queue_size(session_id) == 0

    async def test_delete_session(self) -> None:
        """Test deleting a session."""
        storage = InMemoryStorage()

        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session = Session(session_id=uuid4(), capabilities=caps)
        await storage.save_session(session)

        # Verify session exists
        assert await storage.get_session(session.session_id) is not None

        # Delete session
        await storage.delete_session(session.session_id)

        # Verify session is gone
        assert await storage.get_session(session.session_id) is None

    async def test_get_queue_size_empty(self) -> None:
        """Test getting queue size for empty queue."""
        storage = InMemoryStorage()

        session_id = uuid4()
        queue_size = await storage.get_queue_size(session_id)

        assert queue_size == 0

    async def test_dequeue_from_empty_queue(self) -> None:
        """Test dequeuing from empty queue."""
        storage = InMemoryStorage()

        session_id = uuid4()
        messages = await storage.dequeue_messages(session_id)

        assert messages == []

    async def test_clear_empty_queue(self) -> None:
        """Test clearing an empty queue."""
        storage = InMemoryStorage()

        session_id = uuid4()
        cleared = await storage.clear_queue(session_id)

        assert cleared == 0

    async def test_session_list_by_status(self) -> None:
        """Test listing sessions by status."""
        storage = InMemoryStorage()

        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session1 = Session(session_id=uuid4(), status="active", capabilities=caps)
        session2 = Session(session_id=uuid4(), status="disconnected", capabilities=caps)
        session3 = Session(session_id=uuid4(), status="active", capabilities=caps)

        await storage.save_session(session1)
        await storage.save_session(session2)
        await storage.save_session(session3)

        active_sessions = await storage.list_sessions(status="active")
        assert len(active_sessions) == 2

        disconnected_sessions = await storage.list_sessions(status="disconnected")
        assert len(disconnected_sessions) == 1

    async def test_protocol_not_found(self) -> None:
        """Test getting non-existent protocol."""
        storage = InMemoryStorage()

        protocol = await storage.get_protocol("nonexistent", "1.0.0")

        assert protocol is None

    async def test_message_queue_fifo_order(self) -> None:
        """Test that messages are dequeued in FIFO order."""
        storage = InMemoryStorage()

        session_id = uuid4()
        sender_id = uuid4()

        # Enqueue messages in specific order
        for i in range(5):
            message = Message(
                sender_id=sender_id,
                recipient_id=session_id,
                protocol_name="test",
                protocol_version="1.0.0",
                payload={"order": i},
            )
            await storage.enqueue_message(session_id, message)

        # Dequeue and verify order
        messages = await storage.dequeue_messages(session_id, limit=10)
        assert len(messages) == 5

        for i, msg in enumerate(messages):
            assert msg.payload["order"] == i

    async def test_dequeue_partial_queue(self) -> None:
        """Test dequeuing partial messages from queue."""
        storage = InMemoryStorage()

        session_id = uuid4()
        sender_id = uuid4()

        # Enqueue 5 messages
        for i in range(5):
            message = Message(
                sender_id=sender_id,
                recipient_id=session_id,
                protocol_name="test",
                protocol_version="1.0.0",
                payload={"order": i},
            )
            await storage.enqueue_message(session_id, message)

        # Dequeue only 2
        messages = await storage.dequeue_messages(session_id, limit=2)
        assert len(messages) == 2

        # Remaining should still be there
        queue_size = await storage.get_queue_size(session_id)
        assert queue_size == 3

    async def test_multiple_session_queues(self) -> None:
        """Test that different sessions have separate queues."""
        storage = InMemoryStorage()

        session1_id = uuid4()
        session2_id = uuid4()

        message1 = Message(
            sender_id=uuid4(),
            recipient_id=session1_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"session": 1},
        )

        message2 = Message(
            sender_id=uuid4(),
            recipient_id=session2_id,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"session": 2},
        )

        await storage.enqueue_message(session1_id, message1)
        await storage.enqueue_message(session2_id, message2)

        # Each queue should have 1 message
        assert await storage.get_queue_size(session1_id) == 1
        assert await storage.get_queue_size(session2_id) == 1

        # Clear only one queue
        await storage.clear_queue(session1_id)

        assert await storage.get_queue_size(session1_id) == 0
        assert await storage.get_queue_size(session2_id) == 1
