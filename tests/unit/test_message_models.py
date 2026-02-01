"""
Unit tests for message-related Pydantic models.

Tests the Message, MessageHeaders, DeliveryResult,
BroadcastResult, and EnqueueResult models.
"""

from datetime import UTC, datetime, timedelta

import pytest
from uuid import uuid4

from mcp_broker.models.message import (
    BroadcastResult,
    DeliveryResult,
    EnqueueResult,
    Message,
    MessageHeaders,
    Priority,
)
from tests.conftest import (
    broadcast_message,
    chat_message,
    session_a,
    session_b,
    urgent_message,
)


class TestMessageHeaders:
    """Tests for MessageHeaders model."""

    def test_create_default_headers(self) -> None:
        """Test creating headers with defaults."""
        headers = MessageHeaders()
        assert headers.priority == "normal"
        assert headers.ttl is None
        assert headers.custom == {}

    def test_create_full_headers(self) -> None:
        """Test creating headers with all fields."""
        headers = MessageHeaders(
            priority="urgent", ttl=300, custom={"key": "value"}
        )
        assert headers.priority == "urgent"
        assert headers.ttl == 300
        assert headers.custom == {"key": "value"}

    def test_ttl_validation_negative(self) -> None:
        """Test TTL cannot be negative."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            MessageHeaders(ttl=-1)

    def test_ttl_validation_zero(self) -> None:
        """Test TTL can be zero."""
        headers = MessageHeaders(ttl=0)
        assert headers.ttl == 0


class TestMessage:
    """Tests for Message model."""

    def test_create_point_to_point_message(self, chat_message: Message) -> None:
        """Test creating point-to-point message."""
        assert chat_message.sender_id is not None
        assert chat_message.recipient_id is not None
        assert chat_message.protocol_name == "chat_message"
        assert chat_message.protocol_version == "1.0.0"
        assert chat_message.payload["text"] == "Hello, World!"
        assert chat_message.headers is not None

    def test_create_broadcast_message(self, broadcast_message: Message) -> None:
        """Test creating broadcast message."""
        assert broadcast_message.sender_id is not None
        assert broadcast_message.recipient_id is None
        assert broadcast_message.is_broadcast() is True

    def test_payload_not_empty(self) -> None:
        """Test payload cannot be empty."""
        with pytest.raises(ValueError, match="payload cannot be empty"):
            Message(
                sender_id=uuid4(),
                recipient_id=uuid4(),
                protocol_name="test",
                protocol_version="1.0.0",
                payload={},
            )

    def test_is_broadcast_true(self, broadcast_message: Message) -> None:
        """Test is_broadcast returns True for broadcast."""
        assert broadcast_message.is_broadcast() is True

    def test_is_broadcast_false(self, chat_message: Message) -> None:
        """Test is_broadcast returns False for point-to-point."""
        assert chat_message.is_broadcast() is False

    def test_is_expired_no_ttl(self, chat_message: Message) -> None:
        """Test is_expired returns False when no TTL."""
        assert chat_message.is_expired() is False

    def test_is_expired_with_ttl_not_expired(self, urgent_message: Message) -> None:
        """Test is_expired returns False when TTL not elapsed."""
        assert urgent_message.is_expired() is False

    def test_is_expired_with_ttl_expired(self) -> None:
        """Test is_expired returns True when TTL elapsed."""
        old_time = datetime.now(UTC) - timedelta(seconds=400)
        message = Message(
            sender_id=uuid4(),
            recipient_id=uuid4(),
            timestamp=old_time,
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "test"},
            headers=MessageHeaders(ttl=300),
        )
        assert message.is_expired() is True

    def test_message_id_is_uuid(self, chat_message: Message) -> None:
        """Test message_id is valid UUID."""
        assert isinstance(chat_message.message_id, type(uuid4()))

    def test_timestamp_defaults_to_now(self) -> None:
        """Test timestamp defaults to current time."""
        before = datetime.now(UTC)
        message = Message(
            sender_id=uuid4(),
            recipient_id=uuid4(),
            protocol_name="test",
            protocol_version="1.0.0",
            payload={"data": "test"},
        )
        after = datetime.now(UTC)
        assert before <= message.timestamp <= after


class TestDeliveryResult:
    """Tests for DeliveryResult model."""

    def test_create_success_result(self) -> None:
        """Test creating successful delivery result."""
        result = DeliveryResult(
            success=True,
            delivered_at=datetime.now(UTC),
            message_id=uuid4(),
        )
        assert result.success is True
        assert result.delivered_at is not None
        assert result.error_reason is None
        assert result.queued is False

    def test_create_failure_result(self) -> None:
        """Test creating failed delivery result."""
        result = DeliveryResult(
            success=False,
            error_reason="Session not found",
        )
        assert result.success is False
        assert result.error_reason == "Session not found"
        assert result.delivered_at is None

    def test_create_queued_result(self) -> None:
        """Test creating queued delivery result."""
        result = DeliveryResult(
            success=True,
            queued=True,
            queue_size=5,
        )
        assert result.success is True
        assert result.queued is True
        assert result.queue_size == 5


class TestBroadcastResult:
    """Tests for BroadcastResult model."""

    def test_create_successful_broadcast(self) -> None:
        """Test creating successful broadcast result."""
        result = BroadcastResult(
            success=True,
            delivery_count=2,
            recipients={
                "delivered": [uuid4(), uuid4()],
                "failed": [],
                "skipped": [],
            },
        )
        assert result.success is True
        assert result.delivery_count == 2
        assert len(result.recipients["delivered"]) == 2

    def test_create_failed_broadcast(self) -> None:
        """Test creating failed broadcast result."""
        result = BroadcastResult(
            success=False,
            delivery_count=0,
            reason="No compatible recipients",
        )
        assert result.success is False
        assert result.delivery_count == 0
        assert result.reason == "No compatible recipients"

    def test_recipients_with_all_categories(self) -> None:
        """Test broadcast result with all recipient categories."""
        result = BroadcastResult(
            success=True,
            delivery_count=1,
            recipients={
                "delivered": [uuid4()],
                "failed": [uuid4()],
                "skipped": [uuid4()],
            },
        )
        assert len(result.recipients["delivered"]) == 1
        assert len(result.recipients["failed"]) == 1
        assert len(result.recipients["skipped"]) == 1


class TestEnqueueResult:
    """Tests for EnqueueResult model."""

    def test_create_success_enqueue(self) -> None:
        """Test creating successful enqueue result."""
        result = EnqueueResult(success=True, queue_size=10)
        assert result.success is True
        assert result.queue_size == 10
        assert result.error_reason is None

    def test_create_failure_enqueue(self) -> None:
        """Test creating failed enqueue result."""
        result = EnqueueResult(
            success=False,
            queue_size=100,
            error_reason="Queue full",
        )
        assert result.success is False
        assert result.queue_size == 100
        assert result.error_reason == "Queue full"
