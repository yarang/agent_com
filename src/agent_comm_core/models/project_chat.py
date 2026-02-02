"""
Project chat message models for direct project-based messaging.

Provides models for chat-like messaging within projects,
similar to Discord/Slack channels.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """Types of project messages."""

    STATEMENT = "statement"
    QUESTION = "question"
    ANSWER = "answer"
    NOTIFICATION = "notification"


class ProjectMessageCreate(BaseModel):
    """Request model for creating a new project message."""

    from_agent: str = Field(..., description="Sender agent identifier", min_length=1)
    content: str = Field(..., description="Message content", min_length=1, max_length=10000)
    message_type: MessageType = Field(
        default=MessageType.STATEMENT, description="Type of message"
    )
    in_reply_to: str | None = Field(default=None, description="ID of message this replies to")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProjectMessage(BaseModel):
    """Complete project message model."""

    message_id: str = Field(
        default_factory=lambda: f"msg-{uuid4()}", description="Unique message identifier"
    )
    project_id: str = Field(..., description="Project ID this message belongs to")
    from_agent: str = Field(..., description="Sender agent identifier")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.STATEMENT, description="Message type")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Message timestamp"
    )
    in_reply_to: str | None = Field(default=None, description="ID of message this replies to")
    reactions: list[str] = Field(default_factory=list, description="Message reactions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content."""
        if len(v) > 10000:
            raise ValueError("Content exceeds maximum length of 10,000 characters")
        return v


class AgentAssignment(BaseModel):
    """Agent-to-project assignment model."""

    agent_id: str = Field(..., description="Agent identifier")
    project_id: str = Field(..., description="Project identifier")
    role: str = Field(default="member", description="Agent role in project")
    assigned_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Assignment timestamp"
    )
    assigned_by: str = Field(..., description="Who made the assignment")


class ProjectChatRoom(BaseModel):
    """State of a project chat room."""

    project_id: str = Field(..., description="Project identifier")
    messages: list[ProjectMessage] = Field(default_factory=list, description="Room messages")
    participants: list[str] = Field(default_factory=list, description="Connected agent IDs")
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last activity timestamp"
    )
    unread_count: int = Field(default=0, description="Number of unread messages")


class ProjectCreateRequest(BaseModel):
    """Request to create a project."""

    project_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list)


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    status: str | None = Field(None, pattern=r"^(active|inactive|suspended)$")


class AgentAssignmentRequest(BaseModel):
    """Request to assign agent to project."""

    agent_id: str = Field(..., description="Agent ID to assign")
    role: str = Field(default="member", description="Agent role in project")
