"""
Project API Key database model for MCP broker projects.

This model stores API keys for the ProjectRegistry system with secure hashing.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from agent_comm_core.db.base import Base

if TYPE_CHECKING:
    pass


class ProjectApiKeyDB(Base):
    """
    Database model for project API keys in the MCP broker system.

    Stores API keys with SHA-256 hashing for security.
    The full API key is never stored, only the hash and a prefix for identification.

    API Key Format: {project_id}_{key_id}_{secret}
    Stored: hash(api_key) + prefix (first 20 chars)
    """

    __tablename__ = "project_api_keys"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Project binding (for multi-tenancy)
    project_uuid: Mapped[UUID] = mapped_column(
        "project_uuid",
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Key identifier (human-readable, unique)
    key_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # API key hash (SHA-256) - never store the full key
    api_key_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Key prefix (first 20 chars for identification)
    key_prefix: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Key status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Expiration (optional)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Creator tracking (user who created this key)
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Constraints
    __table_args__ = (UniqueConstraint("project_uuid", "key_id", name="uq_project_key_id"),)

    def __repr__(self) -> str:
        return f"<ProjectApiKeyDB(id={self.id}, key_id={self.key_id}, project_uuid={self.project_uuid})>"

    @property
    def is_valid(self) -> bool:
        """Check if key is active and not expired."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.now(UTC):
            return False
        return True
