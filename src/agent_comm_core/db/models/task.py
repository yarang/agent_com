"""
Task database model for agent task persistence.

This module provides the TaskDB model for storing agent task entities
in the database, enabling proper task tracking and dependency management.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_comm_core.db.base import Base
from agent_comm_core.models.common import TaskPriority, TaskStatus

if TYPE_CHECKING:
    pass

# Re-export enums for API usage
__all__ = ["TaskDB", "TaskStatus", "TaskPriority"]


class TaskDB(Base):
    """
    Database model for agent tasks.

    Tasks represent work items that can be assigned to agents or users
    with status tracking and dependency management.

    This model provides proper persistence for task data, fixing the issue
    where tasks were only stored in memory and lost on refresh.
    """

    __tablename__ = "tasks"

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

    # Optional chat room association
    room_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("chat_rooms.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )

    # Task details
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TaskStatus.PENDING.value,
        index=True,
    )
    priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    # Assignment
    assigned_to: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        default=None,
        index=True,
    )
    assigned_to_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,  # "agent" or "user"
    )

    # Creator tracking
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # Dependencies (JSON array of task IDs)
    dependencies: Mapped[list[UUID]] = mapped_column(
        "dependencies",
        JSON,
        nullable=False,
        default=list,
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Result (JSON object for task output)
    result: Mapped[dict | None] = mapped_column(
        "result",
        JSON,
        nullable=True,
        default=None,
    )

    # Relationships
    project = relationship("ProjectDB", backref="tasks")
    room = relationship("ChatRoomDB", backref="tasks")
    creator = relationship("UserDB", backref="created_tasks")

    def __repr__(self) -> str:
        return f"<TaskDB(id={self.id}, title={self.title}, status={self.status})>"

    @property
    def is_overdue(self) -> bool:
        """Check if task is past due date."""
        if not self.due_date:
            return False
        return self.due_date < datetime.now(UTC)

    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == TaskStatus.COMPLETED.value

    @property
    def can_start(self) -> bool:
        """Check if all dependencies are satisfied.

        Note: This is a simplified check. In production, you would
        query the database to verify all dependency tasks exist
        and are completed.
        """
        # Simplified - assumes dependencies list is checked elsewhere
        return self.status == TaskStatus.PENDING.value
