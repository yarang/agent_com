"""
Meeting models for agent coordination and discussion.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class MeetingStatus(str, Enum):
    """Status of a meeting."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MeetingBase(BaseModel):
    """Base meeting model."""

    title: str = Field(..., description="Meeting title", min_length=1, max_length=200)
    description: Optional[str] = Field(
        default=None, description="Meeting description", max_length=2000
    )
    agenda: list[str] = Field(default_factory=list, description="Agenda items for the meeting")
    max_duration_seconds: Optional[int] = Field(
        default=None, description="Maximum meeting duration in seconds"
    )


class MeetingCreate(MeetingBase):
    """Model for creating a new meeting."""

    participant_ids: list[str] = Field(
        ..., description="List of participant agent IDs", min_length=1
    )


class Meeting(MeetingBase):
    """Complete meeting model with database fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique meeting ID")
    status: MeetingStatus = Field(
        default=MeetingStatus.PENDING, description="Current meeting status"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Meeting start time")
    ended_at: Optional[datetime] = Field(default=None, description="Meeting end time")

    model_config = {"from_attributes": True}

    @field_validator("max_duration_seconds")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Validate maximum duration."""
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        if v is not None and v > 86400:  # 24 hours
            raise ValueError("Duration cannot exceed 24 hours")
        return v


class MeetingParticipantBase(BaseModel):
    """Base meeting participant model."""

    meeting_id: UUID = Field(..., description="Meeting ID")
    agent_id: str = Field(..., description="Agent identifier", min_length=1)
    role: str = Field(default="participant", description="Participant role")


class MeetingParticipantCreate(MeetingParticipantBase):
    """Model for creating a new meeting participant."""

    pass


class MeetingParticipant(MeetingParticipantBase):
    """Complete meeting participant model with database fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique participant ID")
    joined_at: datetime = Field(default_factory=datetime.utcnow, description="Join timestamp")
    left_at: Optional[datetime] = Field(default=None, description="Leave timestamp")

    model_config = {"from_attributes": True}


class MeetingMessageBase(BaseModel):
    """Base meeting message model."""

    meeting_id: UUID = Field(..., description="Meeting ID")
    agent_id: str = Field(..., description="Agent identifier", min_length=1)
    content: str = Field(..., description="Message content")
    message_type: str = Field(
        default="statement", description="Message type (statement, question, answer, etc.)"
    )


class MeetingMessageCreate(MeetingMessageBase):
    """Model for creating a new meeting message."""

    pass


class MeetingMessage(MeetingMessageBase):
    """Complete meeting message model with database fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique message ID")
    sequence_number: int = Field(..., description="Message sequence in meeting")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    in_reply_to: Optional[UUID] = Field(default=None, description="ID of message this replies to")

    model_config = {"from_attributes": True}

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content."""
        if len(v) > 50_000:
            raise ValueError("Content exceeds maximum length of 50,000 characters")
        return v
