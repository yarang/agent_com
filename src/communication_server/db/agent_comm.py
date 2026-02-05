"""
SQLAlchemy ORM models for SPEC-AGENT-COMM-001.

These models implement the database schema as specified in SPEC-AGENT-COMM-001.
They coexist with the existing communication models (CommunicationDB, MeetingDB, etc.)
which have different schemas for other specifications.

Tables:
- agent_comm_communications: Communication logs between agents
- agent_comm_meetings: AI-to-AI meetings for decision making
- agent_comm_meeting_participants: Agents participating in meetings
- agent_comm_meeting_messages: Messages exchanged during meetings
- agent_comm_decisions: Decisions reached during meetings
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base


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


class AgentCommunicationDB(Base):
    """
    SQLAlchemy ORM model for agent communications.

    Implements the communications table from SPEC-AGENT-COMM-001.

    Schema:
        id: UUID primary key
        timestamp: timestamptz (when message was sent)
        sender_id: UUID (agent who sent the message)
        receiver_id: UUID (agent who received the message)
        message_content: TEXT (message content)
        topic: VARCHAR(255) (optional topic categorization)
    """

    __tablename__ = "agent_comm_communications"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    sender_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    receiver_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    message_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    topic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Relationships
    # Note: Decisions can reference communications via related_communication_ids

    __table_args__ = (
        Index("ix_agent_comm_communications_timestamp", "timestamp"),
        Index("ix_agent_comm_communications_sender_id", "sender_id"),
        Index("ix_agent_comm_communications_receiver_id", "receiver_id"),
        Index("ix_agent_comm_communications_topic", "topic"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "sender_id": str(self.sender_id),
            "receiver_id": str(self.receiver_id),
            "message_content": self.message_content,
            "topic": self.topic,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentMeetingDB(Base):
    """
    SQLAlchemy ORM model for agent meetings.

    Implements the meetings table from SPEC-AGENT-COMM-001.

    Schema:
        id: UUID primary key
        topic: VARCHAR(500) (meeting topic)
        meeting_type: ENUM (user_specified, auto_generated)
        status: ENUM (pending, in_progress, completed, failed)
        created_at: timestamptz
        started_at: timestamptz (nullable)
        completed_at: timestamptz (nullable)
        max_discussion_rounds: INT (default 3)
        current_round: INT (default 0)
    """

    __tablename__ = "agent_comm_meetings"

    topic: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    meeting_type: Mapped[MeetingType] = mapped_column(
        SQLEnum(MeetingType),
        default=MeetingType.USER_SPECIFIED,
        nullable=False,
    )
    status: Mapped[MeetingStatus] = mapped_column(
        SQLEnum(MeetingStatus),
        default=MeetingStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    max_discussion_rounds: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    current_round: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    participants: Mapped[list["AgentMeetingParticipantDB"]] = relationship(
        "AgentMeetingParticipantDB",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["AgentMeetingMessageDB"]] = relationship(
        "AgentMeetingMessageDB",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
    decisions: Mapped[list["AgentDecisionDB"]] = relationship(
        "AgentDecisionDB",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_agent_comm_meetings_status", "status"),
        Index("ix_agent_comm_meetings_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "topic": self.topic,
            "meeting_type": self.meeting_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "max_discussion_rounds": self.max_discussion_rounds,
            "current_round": self.current_round,
        }


class AgentMeetingParticipantDB(Base):
    """
    SQLAlchemy ORM model for meeting participants.

    Implements the meeting_participants table from SPEC-AGENT-COMM-001.

    Schema:
        id: UUID primary key
        meeting_id: UUID (foreign key to meetings)
        agent_id: UUID (agent identifier)
        joined_at: timestamptz
        role: VARCHAR(50) (moderator or participant)
        speaking_order: INT (optional, for sequential discussion)
    """

    __tablename__ = "agent_comm_meeting_participants"

    meeting_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_comm_meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="participant",
        nullable=False,
    )
    speaking_order: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationship
    meeting: Mapped["AgentMeetingDB"] = relationship(
        "AgentMeetingDB",
        back_populates="participants",
    )

    __table_args__ = (
        Index("ix_agent_comm_meeting_participants_meeting_id", "meeting_id"),
        Index("ix_agent_comm_meeting_participants_agent_id", "agent_id"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "meeting_id": str(self.meeting_id),
            "agent_id": str(self.agent_id),
            "role": self.role,
            "joined_at": self.created_at.isoformat() if self.created_at else None,
            "speaking_order": self.speaking_order,
        }


class AgentMeetingMessageDB(Base):
    """
    SQLAlchemy ORM model for meeting messages.

    Implements the meeting_messages table from SPEC-AGENT-COMM-001.

    Schema:
        id: UUID primary key
        meeting_id: UUID (foreign key to meetings)
        agent_id: UUID (agent identifier)
        message_content: TEXT
        sequence_number: INT (for ordering messages within a meeting)
        message_type: ENUM (opinion, consensus, meta)
        timestamp: timestamptz
    """

    __tablename__ = "agent_comm_meeting_messages"

    meeting_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_comm_meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )
    message_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    message_type: Mapped[MessageType] = mapped_column(
        SQLEnum(MessageType),
        default=MessageType.OPINION,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationship
    meeting: Mapped["AgentMeetingDB"] = relationship(
        "AgentMeetingDB",
        back_populates="messages",
    )

    __table_args__ = (
        Index("ix_agent_comm_meeting_messages_meeting_id", "meeting_id"),
        Index(
            "ix_agent_comm_meeting_messages_meeting_sequence",
            "meeting_id",
            "sequence_number",
            unique=True,
        ),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "meeting_id": str(self.meeting_id),
            "agent_id": str(self.agent_id),
            "message_content": self.message_content,
            "sequence_number": self.sequence_number,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
        }


class AgentDecisionDB(Base):
    """
    SQLAlchemy ORM model for decisions.

    Implements the decisions table from SPEC-AGENT-COMM-001.

    Schema:
        id: UUID primary key
        meeting_id: UUID (foreign key to meetings)
        decision_content: TEXT
        rationale: TEXT
        related_communication_ids: UUID[] (array of communication IDs)
        participant_agreement: JSONB
        created_at: timestamptz
    """

    __tablename__ = "agent_comm_decisions"

    meeting_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agent_comm_meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    related_communication_ids: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    participant_agreement: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationship
    meeting: Mapped["AgentMeetingDB"] = relationship(
        "AgentMeetingDB",
        back_populates="decisions",
    )

    __table_args__ = (
        Index("ix_agent_comm_decisions_meeting_id", "meeting_id"),
        Index("ix_agent_comm_decisions_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "meeting_id": str(self.meeting_id),
            "decision_content": self.decision_content,
            "rationale": self.rationale,
            "related_communication_ids": [str(cid) for cid in self.related_communication_ids],
            "participant_agreement": self.participant_agreement,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Update the __init__.py to export these models
__all__ = [
    "AgentCommunicationDB",
    "AgentMeetingDB",
    "AgentMeetingParticipantDB",
    "AgentMeetingMessageDB",
    "AgentDecisionDB",
    "MeetingStatus",
    "MeetingType",
    "MessageType",
]
