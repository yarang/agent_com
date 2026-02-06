"""
Chat room database models for real-time messaging.

Provides models for chat rooms, participants, and messages with support
for both users and agents as participants.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base

if TYPE_CHECKING:
    pass


class MessageType(str, Enum):
    """Types of chat messages."""

    TEXT = "text"
    SYSTEM = "system"
    FILE = "file"
    EMBEDDING = "embedding"


class SenderType(str, Enum):
    """Types of message senders."""

    USER = "user"
    AGENT = "agent"


class ChatRoomDB(Base):
    """
    Database model for chat rooms.

    Chat rooms are associated with projects and support real-time messaging
    between users and agents.
    """

    __tablename__ = "chat_rooms"

    # Primary key inherited from Base (id, created_at, updated_at)

    # Project association
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Room details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Creator (human user)
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Relationships
    project = relationship("ProjectDB", backref="chat_rooms")
    creator = relationship("UserDB", backref="created_chat_rooms")
    participants = relationship(
        "ChatParticipantDB", back_populates="room", cascade="all, delete-orphan"
    )
    messages = relationship("ChatMessageDB", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChatRoomDB(id={self.id}, name={self.name}, project_id={self.project_id})>"


class ChatParticipantDB(Base):
    """
    Database model for chat room participants.

    Represents either a user or an agent participating in a chat room.
    """

    __tablename__ = "chat_participants"

    # Primary key inherited from Base

    # Room association
    room_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Participant (either agent or user, not both)
    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )

    # Join timestamp (in addition to created_at)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    room = relationship("ChatRoomDB", back_populates="participants")
    agent = relationship("AgentDB", back_populates="participants")

    # Constraints
    __table_args__ = (
        UniqueConstraint("room_id", "agent_id", name="uq_room_agent"),
        UniqueConstraint("room_id", "user_id", name="uq_room_user"),
    )

    def __repr__(self) -> str:
        participant = f"agent_id={self.agent_id}" if self.agent_id else f"user_id={self.user_id}"
        return f"<ChatParticipantDB(id={self.id}, {participant}, room_id={self.room_id})>"


class ChatMessageDB(Base):
    """
    Database model for chat messages.

    Messages can be sent by users or agents and support various types
    including text, system messages, and file attachments.
    """

    __tablename__ = "chat_messages"

    # Primary key inherited from Base

    # Room association
    room_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sender info
    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SenderType.USER.value,
    )
    sender_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )

    # Message content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MessageType.TEXT.value,
    )

    # Additional metadata (JSON for SQLite/PostgreSQL compatibility)
    meta: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=None,
    )

    # Relationships
    room = relationship("ChatRoomDB", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<ChatMessageDB(id={self.id}, room_id={self.room_id}, "
            f"sender_type={self.sender_type}, sender_id={self.sender_id})>"
        )
