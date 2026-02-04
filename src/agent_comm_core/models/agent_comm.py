"""
Pydantic models for SPEC-AGENT-COMM-001.

These models implement the API schemas as specified in SPEC-AGENT-COMM-001.
They are used for request/response validation in the API layer.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MeetingStatus(str, Enum):
    """Status of a meeting as per SPEC-AGENT-COMM-001."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MeetingType(str, Enum):
    """Type of meeting as per SPEC-AGENT-COMM-001."""

    USER_SPECIFIED = "user_specified"
    AUTO_GENERATED = "auto_generated"


class MessageType(str, Enum):
    """Type of meeting message as per SPEC-AGENT-COMM-001."""

    OPINION = "opinion"
    CONSENSUS = "consensus"
    META = "meta"


# ============================================================================
# Communication Models
# ============================================================================


class CommunicationBase(BaseModel):
    """Base model for communication."""

    sender_id: UUID = Field(..., description="Agent who sent the message")
    receiver_id: UUID = Field(..., description="Agent who received the message")
    message_content: str = Field(
        ..., min_length=1, max_length=10_485_760, description="Message content (max 10MB)"
    )
    topic: str | None = Field(None, max_length=255, description="Optional topic categorization")


class CommunicationCreate(CommunicationBase):
    """Model for creating a communication."""

    pass


class CommunicationResponse(CommunicationBase):
    """Model for communication response."""

    id: UUID = Field(..., description="Unique identifier")
    timestamp: datetime = Field(..., description="When the message was sent")
    created_at: datetime = Field(..., description="Database creation timestamp")

    model_config = {"from_attributes": True}


class CommunicationListResponse(BaseModel):
    """Model for paginated communication list response."""

    communications: list[CommunicationResponse]
    total: int = Field(..., ge=0, description="Total number of communications")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")


# ============================================================================
# Meeting Models
# ============================================================================


class MeetingBase(BaseModel):
    """Base model for meeting."""

    topic: str = Field(..., min_length=1, max_length=500, description="Meeting topic")
    meeting_type: MeetingType = Field(
        default=MeetingType.USER_SPECIFIED, description="Meeting type"
    )
    max_discussion_rounds: int = Field(
        default=3, ge=1, le=10, description="Maximum discussion rounds"
    )


class MeetingCreate(MeetingBase):
    """Model for creating a meeting."""

    participant_ids: list[UUID] = Field(
        ..., min_length=2, description="List of participant agent IDs"
    )


class MeetingResponse(MeetingBase):
    """Model for meeting response."""

    id: UUID = Field(..., description="Unique identifier")
    status: MeetingStatus = Field(..., description="Meeting status")
    created_at: datetime = Field(..., description="Meeting creation timestamp")
    started_at: datetime | None = Field(None, description="Meeting start timestamp")
    completed_at: datetime | None = Field(None, description="Meeting completion timestamp")
    current_round: int = Field(default=0, ge=0, description="Current discussion round")

    model_config = {"from_attributes": True}


class MeetingDetailResponse(MeetingResponse):
    """Model for detailed meeting response with participants and messages."""

    participant_ids: list[UUID] = Field(default_factory=list, description="Participant agent IDs")
    participants: list["MeetingParticipantResponse"] = Field(
        default_factory=list, description="Participant details"
    )
    messages: list["MeetingMessageResponse"] = Field(
        default_factory=list, description="Meeting messages"
    )
    decision: Optional["DecisionResponse"] = Field(None, description="Meeting decision (if any)")


# ============================================================================
# Meeting Participant Models
# ============================================================================


class MeetingParticipantBase(BaseModel):
    """Base model for meeting participant."""

    meeting_id: UUID = Field(..., description="Meeting ID")
    agent_id: UUID = Field(..., description="Agent identifier")
    role: str = Field(default="participant", max_length=50, description="Participant role")
    speaking_order: int | None = Field(
        None, ge=1, description="Speaking order for sequential discussion"
    )


class MeetingParticipantCreate(BaseModel):
    """Model for adding a participant to a meeting."""

    agent_id: UUID = Field(..., description="Agent identifier")
    role: str = Field(default="participant", max_length=50, description="Participant role")


class MeetingParticipantResponse(MeetingParticipantBase):
    """Model for meeting participant response."""

    id: UUID = Field(..., description="Unique identifier")
    joined_at: datetime = Field(..., description="When the participant joined")

    model_config = {"from_attributes": True}


# ============================================================================
# Meeting Message Models
# ============================================================================


class MeetingMessageBase(BaseModel):
    """Base model for meeting message."""

    meeting_id: UUID = Field(..., description="Meeting ID")
    agent_id: UUID = Field(..., description="Agent identifier")
    message_content: str = Field(..., min_length=1, description="Message content")
    message_type: MessageType = Field(default=MessageType.OPINION, description="Message type")


class MeetingMessageCreate(MeetingMessageBase):
    """Model for creating a meeting message."""

    pass


class MeetingMessageResponse(MeetingMessageBase):
    """Model for meeting message response."""

    id: UUID = Field(..., description="Unique identifier")
    sequence_number: int = Field(..., ge=1, description="Message sequence number")
    timestamp: datetime = Field(..., description="Message timestamp")

    model_config = {"from_attributes": True}


# ============================================================================
# Decision Models
# ============================================================================


class DecisionBase(BaseModel):
    """Base model for decision."""

    meeting_id: UUID = Field(..., description="Meeting ID")
    decision_content: str = Field(..., min_length=1, description="Decision content")
    rationale: str | None = Field(None, description="Decision rationale")
    related_communication_ids: list[UUID] = Field(
        default_factory=list, description="Related communication IDs"
    )
    participant_agreement: dict = Field(
        default_factory=dict, description="Participant agreement status"
    )


class DecisionCreate(DecisionBase):
    """Model for creating a decision."""

    pass


class DecisionResponse(DecisionBase):
    """Model for decision response."""

    id: UUID = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Decision creation timestamp")

    model_config = {"from_attributes": True}


class DecisionListResponse(BaseModel):
    """Model for paginated decision list response."""

    decisions: list[DecisionResponse]
    total: int = Field(..., ge=0, description="Total number of decisions")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")


# ============================================================================
# Topic Suggestion Models
# ============================================================================


class SuggestedTopic(BaseModel):
    """Model for a suggested meeting topic."""

    topic: str = Field(..., description="Suggested topic")
    priority: float = Field(..., ge=0.0, le=1.0, description="Topic priority score")
    reason: str = Field(..., description="Reason for suggestion")
    related_communications: list[UUID] = Field(
        default_factory=list, description="Related communication IDs"
    )


class TopicSuggestionResponse(BaseModel):
    """Model for topic suggestion response."""

    suggested_topics: list[SuggestedTopic]
    time_range_hours: int = Field(..., ge=1, description="Time range analyzed in hours")


# ============================================================================
# WebSocket Event Models
# ============================================================================


class WebSocketEventType(str, Enum):
    """WebSocket event types."""

    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

    # Meeting events
    MEETING_STARTED = "meeting_started"
    MEETING_ENDED = "meeting_ended"
    AGENT_JOINED = "agent_joined"
    AGENT_LEFT = "agent_left"

    # Discussion events
    OPINION_REQUEST = "opinion_request"
    OPINION_PRESENTED = "opinion_presented"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_REACHED = "consensus_reached"
    NO_CONSENSUS = "no_consensus"

    # Direct messaging
    DIRECT_MESSAGE = "direct_message"


class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""

    type: str = Field(..., description="Message type")
    meeting_id: UUID | None = Field(None, description="Meeting ID (if applicable)")


class OpinionRequestMessage(WebSocketMessage):
    """Message requesting an opinion from an agent."""

    type: Literal[WebSocketEventType.OPINION_REQUEST.value]
    round: int = Field(..., ge=1, description="Discussion round number")
    topic: str = Field(..., description="Topic to discuss")


class OpinionMessage(BaseModel):
    """Message containing an agent's opinion."""

    type: Literal["opinion"]
    meeting_id: UUID = Field(..., description="Meeting ID")
    agent_id: UUID = Field(..., description="Agent ID")
    content: str = Field(..., min_length=1, description="Opinion content")


class ConsensusRequestMessage(WebSocketMessage):
    """Message requesting consensus vote."""

    type: Literal[WebSocketEventType.CONSENSUS_REQUEST.value]
    opinions: list[dict] = Field(..., description="All opinions collected")


class ConsensusVoteMessage(BaseModel):
    """Message containing an agent's consensus vote."""

    type: Literal["consensus_vote"]
    meeting_id: UUID = Field(..., description="Meeting ID")
    agent_id: UUID = Field(..., description="Agent ID")
    agrees: bool = Field(..., description="Whether agent agrees")


class MeetingEventMessage(WebSocketMessage):
    """Message for meeting events."""

    event: WebSocketEventType = Field(..., description="Event type")
    data: dict = Field(default_factory=dict, description="Event data")


# Update forward references
MeetingDetailResponse.model_rebuild()


__all__ = [
    # Enums
    "MeetingStatus",
    "MeetingType",
    "MessageType",
    "WebSocketEventType",
    # Communication models
    "CommunicationCreate",
    "CommunicationResponse",
    "CommunicationListResponse",
    # Meeting models
    "MeetingCreate",
    "MeetingResponse",
    "MeetingDetailResponse",
    # Participant models
    "MeetingParticipantCreate",
    "MeetingParticipantResponse",
    # Message models
    "MeetingMessageCreate",
    "MeetingMessageResponse",
    # Decision models
    "DecisionCreate",
    "DecisionResponse",
    "DecisionListResponse",
    # Topic models
    "SuggestedTopic",
    "TopicSuggestionResponse",
    # WebSocket models
    "WebSocketMessage",
    "OpinionRequestMessage",
    "OpinionMessage",
    "ConsensusRequestMessage",
    "ConsensusVoteMessage",
    "MeetingEventMessage",
]
