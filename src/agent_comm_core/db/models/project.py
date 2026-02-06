"""
Project database model for multi-tenancy support.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base
from agent_comm_core.models.common import ProjectStatus


class ProjectDB(Base):
    """
    Database model for projects (multi-tenancy).

    Projects are owned by users and contain all data (communications, meetings, etc.).
    """

    __tablename__ = "projects"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Owner (human user)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Project identifier (human-readable unique ID)
    project_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Project details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Status and configuration
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProjectStatus.ACTIVE,
        index=True,
    )

    # Allow cross-project access (optional feature)
    allow_cross_project: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Settings (JSON for cross-database compatibility)
    settings: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
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

    # Relationships
    owner = relationship("UserDB", backref="projects")
    agents = relationship("AgentDB", back_populates="project")

    # Constraints
    __table_args__ = (UniqueConstraint("owner_id", "project_id", name="uq_owner_project_id"),)

    def __repr__(self) -> str:
        return f"<ProjectDB(id={self.id}, project_id={self.project_id}, owner_id={self.owner_id})>"

    @property
    def is_active(self) -> bool:
        """Check if project is active."""
        return self.status == ProjectStatus.ACTIVE
