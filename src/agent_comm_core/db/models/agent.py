"""
Agent database model for AI agent persistence.

This module provides the AgentDB model for storing AI agent entities
in the database, enabling proper referential integrity with other tables.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base
from agent_comm_core.models.common import AgentStatus

if TYPE_CHECKING:
    pass


class AgentDB(Base):
    """
    Database model for AI agents.

    Agents are autonomous entities that can participate in chat rooms,
    create API keys, and perform actions on behalf of projects.

    This model provides proper referential integrity for agent_id references
    throughout the system, fixing the issue where agents only existed
    implicitly through their API keys.
    """

    __tablename__ = "agents"

    # Primary key (inherited from Base provides id, created_at, updated_at)
    # Override id to use uuid4 default explicitly
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Project association
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Agent details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    nickname: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    agent_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="generic",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AgentStatus.OFFLINE.value,
        index=True,
    )

    # Capabilities (JSON array for SQLite/PostgreSQL compatibility)
    capabilities: Mapped[list[str]] = mapped_column(
        "capabilities",
        JSON,
        nullable=False,
        default=list,
    )

    # Configuration (JSON object for flexible settings)
    config: Mapped[dict | None] = mapped_column(
        "config",
        JSON,
        nullable=True,
        default=None,
    )

    # Active state
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Relationships
    project = relationship("ProjectDB", back_populates="agents")
    api_keys = relationship("AgentApiKeyDB", back_populates="agent", cascade="all, delete-orphan")
    participants = relationship("ChatParticipantDB", back_populates="agent")
    sent_messages = relationship(
        "ChatMessageDB",
        foreign_keys="ChatMessageDB.agent_sender_id",
        back_populates="agent_sender",
        lazy="selectin",
    )
    assigned_tasks = relationship(
        "TaskDB",
        foreign_keys="TaskDB.agent_assigned_to",
        back_populates="assigned_agent",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_agent_project_name"),)

    def __repr__(self) -> str:
        return f"<AgentDB(id={self.id}, name={self.name}, project_id={self.project_id})>"

    @property
    def is_online(self) -> bool:
        """Check if agent is currently online."""
        return self.status == AgentStatus.ONLINE and self.is_active


# Import JSON type for SQLAlchemy compatibility
