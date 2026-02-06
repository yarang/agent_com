"""
Task API endpoints for TaskDB CRUD operations.

Provides REST API for managing tasks with project-level authorization
and dependency tracking.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.database import db_session
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.task import TaskDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.common import TaskStatus
from agent_comm_core.models.schemas.task import (
    TaskAssignRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# =============================================================================
# Database Session Dependency
# =============================================================================


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for database session."""
    async with db_session() as session:
        yield session


# ============================================================================
# Response Models
# ============================================================================


class PaginatedTaskResponse(BaseModel):
    """Paginated response for task list."""

    items: list[TaskResponse]
    total: int
    page: int
    size: int
    has_more: bool


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# ============================================================================
# Helper Functions
# ============================================================================


async def _verify_project_access(project_id: UUID, user: User, session: AsyncSession) -> ProjectDB:
    """
    Verify that a user has access to a project.

    Args:
        project_id: Project UUID
        user: Current user
        session: Database session

    Returns:
        ProjectDB instance

    Raises:
        HTTPException: If project not found or access denied
    """
    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다",  # Project not found
        )

    # Check ownership or superuser
    if project.owner_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="프로젝트에 접근할 권한이 없습니다",  # No access to project
        )

    return project


async def _verify_task_dependencies(
    task_id: UUID, dependencies: list[UUID], session: AsyncSession
) -> None:
    """
    Verify that all dependency tasks exist and are completed.

    Args:
        task_id: Current task ID (to exclude from self-dependency check)
        dependencies: List of dependency task IDs
        session: Database session

    Raises:
        HTTPException: If dependency doesn't exist or is not completed
    """
    if not dependencies:
        return

    # Filter out self-reference (for updates)
    filtered_deps = [dep_id for dep_id in dependencies if dep_id != task_id]

    if not filtered_deps:
        return

    # Check if all dependencies exist
    result = await session.execute(select(TaskDB).where(TaskDB.id.in_(filtered_deps)))
    existing_tasks = {t.id: t for t in result.scalars().all()}

    for dep_id in filtered_deps:
        if dep_id not in existing_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"의존 작업 ID {dep_id}를 찾을 수 없습니다",  # Dependency not found
            )

        dep_task = existing_tasks[dep_id]
        if dep_task.status != TaskStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"의존 작업 '{dep_task.title}'이(가) 아직 완료되지 않았습니다",  # Dependency not completed
            )


def _task_db_to_response(task_db: TaskDB) -> TaskResponse:
    """
    Convert TaskDB to TaskResponse.

    Args:
        task_db: Database model

    Returns:
        TaskResponse model
    """
    return TaskResponse.model_validate(task_db)


# ============================================================================
# Task CRUD Endpoints
# ============================================================================


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new task.

    Requires JWT authentication. Dependencies must be completed tasks.

    Args:
        task_data: Task creation data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Created task with id

    Raises:
        HTTPException: 404 if project not found
                        403 if no project access
                        400 if dependencies invalid
    """
    # Verify project access
    project = await _verify_project_access(task_data.project_id, current_user, session)

    # Verify dependencies
    await _verify_task_dependencies(UUID(int=0), task_data.dependencies, session)

    # Create task
    task = TaskDB(
        project_id=project.id,
        room_id=task_data.room_id,
        title=task_data.title,
        description=task_data.description,
        status=TaskStatus.PENDING.value,
        priority=task_data.priority,
        assigned_to=task_data.assigned_to,
        assigned_to_type=task_data.assigned_to_type,
        created_by=current_user.id,
        dependencies=task_data.dependencies,
        due_date=task_data.due_date,
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return _task_db_to_response(task)


@router.get("", response_model=PaginatedTaskResponse)
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    project_id: UUID | None = None,
    room_id: UUID | None = None,
    status: str | None = None,
    assigned_to: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    List tasks with pagination and filtering.

    Requires JWT authentication. Users can only see tasks from their projects.

    Args:
        current_user: Current authenticated user
        session: Database session
        project_id: Optional project UUID filter
        room_id: Optional room UUID filter
        status: Optional status filter
        assigned_to: Optional assignee UUID filter
        page: Page number (1-indexed)
        size: Page size (max 100)

    Returns:
        Paginated list of tasks
    """
    # Build base query
    stmt = select(TaskDB)

    # Filter by project access (owner-only)
    if not current_user.is_superuser:
        # Get user's project IDs
        project_stmt = select(ProjectDB.id).where(ProjectDB.owner_id == current_user.id)
        project_result = await session.execute(project_stmt)
        user_project_ids = [row[0] for row in project_result.fetchall()]
        stmt = stmt.where(TaskDB.project_id.in_(user_project_ids))

    # Apply optional filters
    if project_id:
        stmt = stmt.where(TaskDB.project_id == project_id)
    if room_id:
        stmt = stmt.where(TaskDB.room_id == room_id)
    if status:
        stmt = stmt.where(TaskDB.status == status)
    if assigned_to:
        stmt = stmt.where(TaskDB.assigned_to == assigned_to)

    # Count total for pagination
    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination
    stmt = stmt.order_by(TaskDB.created_at.desc())
    stmt = stmt.offset((page - 1) * size).limit(size)

    result = await session.execute(stmt)
    tasks = result.scalars().all()

    return PaginatedTaskResponse(
        items=[_task_db_to_response(task) for task in tasks],
        total=total,
        page=page,
        size=size,
        has_more=total > page * size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a task by ID with dependencies.

    Requires JWT authentication and project access.

    Args:
        task_id: Task UUID
        current_user: Current authenticated user
        session: Database session

    Returns:
        Task details with dependencies

    Raises:
        HTTPException: 404 if task not found
                        403 if no project access
    """
    result = await session.execute(select(TaskDB).where(TaskDB.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="작업을 찾을 수 없습니다",  # Task not found
        )

    # Check project access
    await _verify_project_access(task.project_id, current_user, session)

    return _task_db_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a task.

    Requires JWT authentication and project access. Supports partial updates.
    Automatically manages status-based timestamps (started_at, completed_at).

    Args:
        task_id: Task UUID
        task_data: Partial update data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found
                        403 if no project access
                        400 if dependencies invalid
    """
    result = await session.execute(select(TaskDB).where(TaskDB.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="작업을 찾을 수 없습니다",  # Task not found
        )

    # Check project access
    await _verify_project_access(task.project_id, current_user, session)

    # Verify dependencies if updated
    if task_data.dependencies is not None:
        await _verify_task_dependencies(task_id, task_data.dependencies, session)

    # Apply updates
    update_data = task_data.model_dump(exclude_unset=True)

    # Auto-manage timestamps based on status
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == TaskStatus.IN_PROGRESS.value and not task.started_at:
            update_data["started_at"] = datetime.now(UTC)
        elif new_status == TaskStatus.COMPLETED.value:
            if not task.started_at:
                update_data["started_at"] = datetime.now(UTC)
            update_data["completed_at"] = datetime.now(UTC)

    for field, value in update_data.items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)

    return _task_db_to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a task.

    Requires JWT authentication and project access.

    Args:
        task_id: Task UUID
        current_user: Current authenticated user
        session: Database session

    Raises:
        HTTPException: 404 if task not found
                        403 if no project access
    """
    result = await session.execute(select(TaskDB).where(TaskDB.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="작업을 찾을 수 없습니다",  # Task not found
        )

    # Check project access
    await _verify_project_access(task.project_id, current_user, session)

    # Delete task
    await session.delete(task)
    await session.commit()


@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: UUID,
    assign_data: TaskAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Assign a task to an agent or user.

    Requires JWT authentication and project access.

    Args:
        task_id: Task UUID
        assign_data: Assignment data with assignee type
        current_user: Current authenticated user
        session: Database session

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found
                        403 if no project access
    """
    result = await session.execute(select(TaskDB).where(TaskDB.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="작업을 찾을 수 없습니다",  # Task not found
        )

    # Check project access
    await _verify_project_access(task.project_id, current_user, session)

    # Update assignment
    task.assigned_to = assign_data.assigned_to
    task.assigned_to_type = assign_data.assigned_to_type

    await session.commit()
    await session.refresh(task)

    return _task_db_to_response(task)


__all__ = ["router"]
