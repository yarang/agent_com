"""
Pydantic schemas for Task API requests and responses.

Provides validation and serialization for task CRUD operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Task Request Schemas
# ============================================================================


class TaskCreate(BaseModel):
    """Request model for creating a new task.

    Fields:
        project_id: Associated project UUID
        room_id: Optional chat room UUID
        title: Task title
        description: Optional detailed description
        priority: Task priority level
        assigned_to: Optional UUID of assignee (agent or user)
        assigned_to_type: Type of assignee ("agent" or "user")
        dependencies: List of task IDs this task depends on
        due_date: Optional deadline for completion
    """

    project_id: UUID = Field(..., description="Associated project UUID")
    room_id: UUID | None = Field(None, description="Optional chat room UUID")
    title: str = Field(..., description="Task title", min_length=1, max_length=500)
    description: str | None = Field(
        None,
        description="Detailed task description",
    )
    priority: str | None = Field(
        None,
        description="Task priority (low, medium, high, critical)",
    )
    assigned_to: UUID | None = Field(None, description="Assignee UUID (agent or user)")
    assigned_to_type: str | None = Field(
        None,
        description="Assignee type ('agent' or 'user')",
    )
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of task IDs this task depends on",
    )
    due_date: datetime | None = Field(None, description="Task deadline")


class TaskUpdate(BaseModel):
    """Request model for updating a task.

    All fields are optional to support partial updates.
    """

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = Field(None, max_length=50)
    priority: str | None = None
    assigned_to: UUID | None = None
    assigned_to_type: str | None = None
    dependencies: list[UUID] | None = None
    due_date: datetime | None = None
    result: dict[str, Any] | None = None


class TaskAssignRequest(BaseModel):
    """Request model for assigning a task.

    Fields:
        assigned_to: UUID of assignee (agent or user)
        assigned_to_type: Type of assignee ("agent" or "user")
    """

    assigned_to: UUID = Field(..., description="Assignee UUID (agent or user)")
    assigned_to_type: str = Field(
        ...,
        description="Assignee type ('agent' or 'user')",
    )


# ============================================================================
# Task Response Schemas
# ============================================================================


class TaskResponse(BaseModel):
    """Response model for task data.

    Represents the complete task state as returned from the API.
    """

    id: UUID = Field(..., description="Task UUID")
    project_id: UUID = Field(..., description="Associated project UUID")
    room_id: UUID | None = Field(None, description="Associated chat room UUID")
    title: str = Field(..., description="Task title")
    description: str | None = Field(None, description="Task description")
    status: str = Field(..., description="Current task status")
    priority: str | None = Field(None, description="Task priority")
    assigned_to: UUID | None = Field(None, description="Assignee UUID")
    assigned_to_type: str | None = Field(None, description="Assignee type")
    created_by: UUID = Field(..., description="Creator UUID")
    dependencies: list[UUID] = Field(..., description="Dependency task IDs")
    started_at: datetime | None = Field(None, description="Task start time")
    completed_at: datetime | None = Field(None, description="Task completion time")
    due_date: datetime | None = Field(None, description="Task deadline")
    result: dict[str, Any] | None = Field(None, description="Task result data")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


__all__ = [
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskAssignRequest",
]
