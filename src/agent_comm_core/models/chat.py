"""
Pydantic models for chat room API requests and responses.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class SenderType(str, Enum):
    """Types of message senders."""

    USER = "user"
    AGENT = "agent"


class MessageType(str, Enum):
    """Types of chat messages."""

    TEXT = "text"
    SYSTEM = "system"
    FILE = "file"


# ============================================================================
# Chat Room Models
# ============================================================================


class ChatRoomCreate(BaseModel):
    """Request model for creating a chat room."""

    project_id: UUID = Field(..., description="Project ID to associate with")
    name: str = Field(..., min_length=1, max_length=255, description="Room name")
    description: str | None = Field(None, max_length=2000, description="Room description")


class ChatRoomUpdate(BaseModel):
    """Request model for updating a chat room."""

    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)


class ChatRoomResponse(BaseModel):
    """Response model for chat room."""

    id: UUID = Field(..., description="Room UUID")
    project_id: UUID = Field(..., description="Associated project UUID")
    name: str = Field(..., description="Room name")
    description: str | None = Field(None, description="Room description")
    created_by: UUID | None = Field(None, description="Creator user UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    participant_count: int = Field(0, description="Number of participants")
    message_count: int = Field(0, description="Number of messages")

    model_config = {"from_attributes": True}


# ============================================================================
# Chat Participant Models
# ============================================================================


class ChatParticipantAdd(BaseModel):
    """Request model for adding a participant to a room."""

    agent_id: UUID | None = Field(None, description="Agent UUID to add")
    user_id: UUID | None = Field(None, description="User UUID to add")


class ChatParticipantResponse(BaseModel):
    """Response model for chat participant."""

    id: UUID = Field(..., description="Participant UUID")
    room_id: UUID = Field(..., description="Room UUID")
    agent_id: UUID | None = Field(None, description="Agent UUID if agent")
    user_id: UUID | None = Field(None, description="User UUID if user")
    joined_at: datetime = Field(..., description="Join timestamp")

    model_config = {"from_attributes": True}


# ============================================================================
# Chat Message Models
# ============================================================================


class ChatMessageCreate(BaseModel):
    """Request model for sending a chat message."""

    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: MessageType = Field(MessageType.TEXT, description="Message type")
    metadata: dict | None = Field(None, description="Additional metadata")


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""

    id: UUID = Field(..., description="Message UUID")
    room_id: UUID = Field(..., description="Room UUID")
    sender_type: SenderType = Field(..., description="Sender type (user or agent)")
    sender_id: UUID = Field(..., description="Sender UUID")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(..., description="Message type")
    metadata: dict | None = Field(None, description="Message metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class ChatMessageListResponse(BaseModel):
    """Response model for paginated message list."""

    messages: list[ChatMessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total message count")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Messages per page")
    has_more: bool = Field(..., description="Whether there are more messages")


# ============================================================================
# WebSocket Event Models
# ============================================================================


class WSChatMessage(BaseModel):
    """WebSocket message format for chat."""

    event: str = Field(..., description="Event type (message, typing, etc.)")
    room_id: UUID = Field(..., description="Room UUID")
    data: dict = Field(..., description="Event data")


class TypingIndicator(BaseModel):
    """Typing indicator data."""

    sender_id: UUID = Field(..., description="Sender UUID")
    sender_type: SenderType = Field(..., description="Sender type")
    is_typing: bool = Field(..., description="Whether currently typing")
