"""
SQLAlchemy ORM models for meetings and related entities.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base


class MeetingStatus(str, Enum):
    """Status of a meeting."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DecisionStatus(str, Enum):
    """Status of a decision."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class MeetingDB(Base):
    """
    SQLAlchemy ORM model for meetings.

    Maps to the Meeting Pydantic model in agent_comm_core.
    """

    __tablename__ = "meetings"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    agenda: Mapped[list] = mapped_column(JSON, default=[], nullable=False)
    max_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(
        SQLEnum(MeetingStatus), default=MeetingStatus.PENDING, nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    participants: Mapped[list["MeetingParticipantDB"]] = relationship(
        "MeetingParticipantDB", back_populates="meeting", cascade="all, delete-orphan"
    )
    messages: Mapped[list["MeetingMessageDB"]] = relationship(
        "MeetingMessageDB", back_populates="meeting", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["DecisionDB"]] = relationship(
        "DecisionDB", back_populates="meeting", cascade="all, delete-orphan"
    )

    def to_pydantic(self):
        """Convert to Pydantic model."""
        from agent_comm_core.models.meeting import Meeting, MeetingStatus

        return Meeting(
            id=self.id,
            title=self.title,
            description=self.description,
            agenda=list(self.agenda) if self.agenda else [],
            max_duration_seconds=self.max_duration_seconds,
            status=MeetingStatus(self.status.value),
            created_at=self.created_at,
            started_at=self.started_at,
            ended_at=self.ended_at,
        )


class MeetingParticipantDB(Base):
    """
    SQLAlchemy ORM model for meeting participants.

    Maps to the MeetingParticipant Pydantic model in agent_comm_core.
    """

    __tablename__ = "meeting_participants"

    meeting_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(100), default="participant", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    meeting: Mapped["MeetingDB"] = relationship("MeetingDB", back_populates="participants")

    def to_pydantic(self):
        """Convert to Pydantic model."""
        from agent_comm_core.models.meeting import MeetingParticipant

        return MeetingParticipant(
            id=self.id,
            meeting_id=self.meeting_id,
            agent_id=self.agent_id,
            role=self.role,
            joined_at=self.joined_at,
            left_at=self.left_at,
        )


class MeetingMessageDB(Base):
    """
    SQLAlchemy ORM model for meeting messages.

    Maps to the MeetingMessage Pydantic model in agent_comm_core.
    """

    __tablename__ = "meeting_messages"

    meeting_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(100), default="statement", nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    in_reply_to: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationship
    meeting: Mapped["MeetingDB"] = relationship("MeetingDB", back_populates="messages")

    def to_pydantic(self):
        """Convert to Pydantic model."""
        from agent_comm_core.models.meeting import MeetingMessage

        return MeetingMessage(
            id=self.id,
            meeting_id=self.meeting_id,
            agent_id=self.agent_id,
            content=self.content,
            message_type=self.message_type,
            sequence_number=self.sequence_number,
            created_at=self.created_at,
            in_reply_to=self.in_reply_to,
        )


class DecisionDB(Base):
    """
    SQLAlchemy ORM model for decisions.

    Maps to the Decision Pydantic model in agent_comm_core.
    """

    __tablename__ = "decisions"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    options: Mapped[list] = mapped_column(JSON, default=[], nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(
        SQLEnum(DecisionStatus), default=DecisionStatus.PENDING, nullable=False, index=True
    )
    meeting_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    selected_option: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationship
    meeting: Mapped["MeetingDB"] = relationship("MeetingDB", back_populates="decisions")

    def to_pydantic(self):
        """Convert to Pydantic model."""
        from agent_comm_core.models.decision import Decision, DecisionStatus

        return Decision(
            id=self.id,
            title=self.title,
            description=self.description,
            context=dict(self.context) if self.context else {},
            proposed_by=self.proposed_by,
            options=list(self.options) if self.options else [],
            status=DecisionStatus(self.status.value),
            meeting_id=self.meeting_id,
            selected_option=self.selected_option,
            rationale=self.rationale,
            deadline=self.deadline,
            decided_at=self.decided_at,
            created_at=self.created_at,
        )
