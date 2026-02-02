"""
Agent API Key database model with structured key format.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from agent_comm_core.db.base import Base


class KeyStatus(str, Enum):
    """Status of an API key."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CreatorType(str, Enum):
    """Type of entity that created the record."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class AgentApiKeyDB(Base):
    """
    Database model for agent API keys with project binding.

    Structured format: sk_agent_v1_{project_id}_{agent_id}_{hash}
    """

    __tablename__ = "agent_api_keys"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Project binding (for multi-tenancy)
    project_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Agent identifier
    agent_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )

    # Key identifier (human-readable)
    key_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # API key hash (SHA-256)
    api_key_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Key prefix (for identification without revealing full key)
    key_prefix: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Capabilities (JSON array for SQLite compatibility)
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # Key status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=KeyStatus.ACTIVE,
        index=True,
    )

    # Expiration (optional)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Creator tracking
    created_by_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CreatorType.USER,
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Constraints
    __table_args__ = (UniqueConstraint("project_id", "agent_id", name="uq_project_agent"),)

    def __repr__(self) -> str:
        return f"<AgentApiKeyDB(id={self.id}, key_id={self.key_id}, agent_id={self.agent_id})>"

    @property
    def is_active(self) -> bool:
        """Check if key is active and not expired."""
        if self.status != KeyStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < datetime.now(UTC):
            return False
        return True
