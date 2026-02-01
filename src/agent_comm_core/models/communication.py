"""
Communication models for logging agent messages.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class CommunicationDirection(str, Enum):
    """Direction of communication."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class CommunicationBase(BaseModel):
    """Base communication model."""

    from_agent: str = Field(..., description="Source agent identifier", min_length=1)
    to_agent: str = Field(..., description="Target agent identifier", min_length=1)
    message_type: str = Field(..., description="Type of message", min_length=1)
    content: str = Field(..., description="Message content")
    direction: CommunicationDirection = Field(
        default=CommunicationDirection.INTERNAL,
        description="Communication direction",
    )
    correlation_id: Optional[UUID] = Field(
        default=None, description="Correlation ID for related messages"
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class CommunicationCreate(CommunicationBase):
    """Model for creating a new communication."""

    pass


class Communication(CommunicationBase):
    """Complete communication model with database fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique communication ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = {"from_attributes": True}

    @field_validator("from_agent", "to_agent")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Validate agent identifier format."""
        if not v or not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content."""
        if len(v) > 100_000:
            raise ValueError("Content exceeds maximum length of 100,000 characters")
        return v
