"""
Pydantic models for message-related data structures.

This module defines the data models for messages, delivery results,
and message routing operations.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# Type aliases for common types
Priority = Literal["low", "normal", "high", "urgent"]


class MessageHeaders(BaseModel):
    """Optional message headers for routing and metadata.

    Attributes:
        priority: Message priority level
        ttl: Time-to-live in seconds
        custom: Custom headers as key-value pairs
    """

    priority: Priority = "normal"
    ttl: int | None = Field(default=None, ge=0, description="Time-to-live in seconds")
    custom: dict[str, str] = Field(default_factory=dict)


class Message(BaseModel):
    """Complete message structure for routing between sessions.

    Attributes:
        message_id: Unique message identifier
        sender_id: Sender session UUID
        recipient_id: Recipient session UUID (None for broadcast)
        timestamp: Message creation timestamp
        protocol_name: Protocol identifier for payload validation
        protocol_version: Protocol version for payload validation
        payload: Message payload (validated against protocol schema)
        headers: Optional message headers
    """

    message_id: UUID = Field(default_factory=uuid4)
    sender_id: UUID
    recipient_id: UUID | None = Field(
        default=None, description="Recipient UUID (None for broadcast)"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    protocol_name: str
    protocol_version: str
    payload: dict
    headers: MessageHeaders | None = None

    @field_validator("payload")
    @classmethod
    def payload_not_empty(cls, v: dict) -> dict:
        """Validate payload is not empty.

        Args:
            v: Payload dictionary

        Returns:
            Validated payload

        Raises:
            ValueError: If payload is empty
        """
        if not v:
            raise ValueError("payload cannot be empty")
        return v

    def is_broadcast(self) -> bool:
        """Check if this is a broadcast message.

        Returns:
            True if message has no specific recipient
        """
        return self.recipient_id is None

    def is_expired(self) -> bool:
        """Check if message has expired based on TTL.

        Returns:
            True if message TTL has elapsed
        """
        if self.headers and self.headers.ttl:
            elapsed = (datetime.now(UTC) - self.timestamp).total_seconds()
            return elapsed > self.headers.ttl
        return False


class DeliveryResult(BaseModel):
    """Result of point-to-point message delivery.

    Attributes:
        success: Whether delivery succeeded
        delivered_at: Timestamp of successful delivery
        error_reason: Human-readable error reason (if failed)
        queued: True if message was queued for offline recipient
        queue_size: Current queue size (if queued)
        message_id: Delivered message ID
    """

    success: bool
    delivered_at: datetime | None = None
    error_reason: str | None = None
    queued: bool = False
    queue_size: int | None = None
    message_id: UUID | None = None


class BroadcastResult(BaseModel):
    """Result of broadcast message delivery.

    Attributes:
        success: Whether broadcast was initiated
        delivery_count: Number of successful deliveries
        recipients: Dict with delivered, failed, and skipped session IDs
        reason: Reason if no recipients were found
    """

    success: bool
    delivery_count: int = 0
    recipients: dict[str, list[UUID]] = Field(
        default_factory=lambda: {"delivered": [], "failed": [], "skipped": []}
    )
    reason: str | None = None


class EnqueueResult(BaseModel):
    """Result of message enqueue operation.

    Attributes:
        success: Whether enqueue succeeded
        queue_size: New queue size after enqueue
        error_reason: Reason for failure (if any)
    """

    success: bool
    queue_size: int = 0
    error_reason: str | None = None
