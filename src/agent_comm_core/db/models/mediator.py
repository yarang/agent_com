"""
Mediator system database models.

Provides models for AI mediators that can participate in chat rooms
to facilitate discussions, summarize conversations, or perform automated tasks.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base


class MediatorModelProvider(str, Enum):
    """LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    CUSTOM = "custom"


class MediatorPromptCategory(str, Enum):
    """Prompt categories for different use cases."""

    MODERATOR = "moderator"
    SUMMARIZER = "summarizer"
    FACILITATOR = "facilitator"
    TRANSLATOR = "translator"
    CODE_REVIEWER = "code_reviewer"
    TECHNICAL_ADVISOR = "technical_advisor"
    CUSTOM = "custom"


class MediatorModelDB(Base):
    """
    Database model for LLM models available for mediators.

    Stores configuration for various LLM providers and models.
    """

    __tablename__ = "mediator_models"

    # Model identifier (human-readable)
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    # Provider information
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Model ID for API calls (e.g., 'gpt-4-turbo-preview', 'claude-3-opus-20240229')
    model_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Optional custom API endpoint
    api_endpoint: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    # Model capabilities and limits
    max_tokens: Mapped[int | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    supports_streaming: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    supports_function_calling: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Cost tracking (cost per 1k tokens in USD)
    cost_per_1k_tokens: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Relationships
    mediators = relationship("MediatorDB", back_populates="model")

    def __repr__(self) -> str:
        return f"<MediatorModelDB(id={self.id}, name={self.name}, provider={self.provider})>"


class MediatorPromptDB(Base):
    """
    Database model for mediator prompts.

    Stores reusable prompts that can be used by mediators.
    """

    __tablename__ = "mediator_prompts"

    # Project association
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Prompt identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Category for organization
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # The actual system prompt
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Configurable variables in the prompt (JSON)
    variables: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )

    # Few-shot examples (JSON)
    examples: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )

    # Sharing options
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Creator
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Relationships
    project = relationship("ProjectDB", backref="mediator_prompts")
    creator = relationship("UserDB", backref="created_prompts")

    def __repr__(self) -> str:
        return f"<MediatorPromptDB(id={self.id}, name={self.name}, category={self.category})>"


class MediatorDB(Base):
    """
    Database model for AI mediators.

    Mediators are AI agents that can participate in chat rooms.
    """

    __tablename__ = "mediators"

    # Project association
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Mediator identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Model configuration
    model_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("mediator_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Default prompt
    default_prompt_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("mediator_prompts.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Optional system prompt override
    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # LLM parameters
    temperature: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default="0.7",
    )

    max_tokens: Mapped[int | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Creator
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Relationships
    project = relationship("ProjectDB", backref="mediators")
    model = relationship("MediatorModelDB", back_populates="mediators")
    default_prompt = relationship("MediatorPromptDB", backref="used_in_mediators")
    creator = relationship("UserDB", backref="created_mediators")
    room_assignments = relationship(
        "ChatRoomMediatorDB", back_populates="mediator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MediatorDB(id={self.id}, name={self.name}, project_id={self.project_id})>"


class ChatRoomMediatorDB(Base):
    """
    Junction table for chat room and mediator assignments.

    Manages which mediators are assigned to which chat rooms
    and their per-room configuration.
    """

    __tablename__ = "chat_room_mediators"

    # Chat room identifier (using project_id as room_id for now)
    room_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Mediator assignment
    mediator_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("mediators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional prompt override for this room
    prompt_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("mediator_prompts.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Trigger configuration
    auto_trigger: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Keywords that trigger this mediator (JSON array for SQLite compatibility)
    trigger_keywords: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )

    # When the mediator joined the room
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    room = relationship("ProjectDB", backref="room_mediators")
    mediator = relationship("MediatorDB", back_populates="room_assignments")
    prompt_override = relationship("MediatorPromptDB", backref="room_assignments")

    def __repr__(self) -> str:
        return f"<ChatRoomMediatorDB(id={self.id}, room_id={self.room_id}, mediator_id={self.mediator_id})>"
