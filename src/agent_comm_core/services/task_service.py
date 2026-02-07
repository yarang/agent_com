"""
Task service with business logic for Task operations.

This service provides comprehensive business logic for managing agent tasks,
including creation, retrieval, updating, deletion, assignment, and status management.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.task import TaskDB
from agent_comm_core.models.common import TaskPriority, TaskStatus
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase


class TaskRepository(SQLAlchemyRepositoryBase):
    """Repository for Task database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, TaskDB)


class AgentRepository(SQLAlchemyRepositoryBase):
    """Repository for Agent database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, AgentDB)


class TaskService:
    """
    Service for managing agent tasks with business logic.

    Provides operations for creating, retrieving, updating, and deleting tasks,
    as well as managing task assignment, status, and dependency validation.
    """

    # Valid status transitions for tasks
    VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
        TaskStatus.PENDING.value: [
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.BLOCKED.value,
            TaskStatus.CANCELLED.value,
        ],
        TaskStatus.IN_PROGRESS.value: [
            TaskStatus.REVIEW.value,
            TaskStatus.BLOCKED.value,
            TaskStatus.PENDING.value,
            TaskStatus.CANCELLED.value,
            TaskStatus.COMPLETED.value,
        ],
        TaskStatus.REVIEW.value: [
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.COMPLETED.value,
            TaskStatus.PENDING.value,
            TaskStatus.CANCELLED.value,
        ],
        TaskStatus.BLOCKED.value: [
            TaskStatus.PENDING.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.CANCELLED.value,
        ],
        TaskStatus.COMPLETED.value: [
            TaskStatus.IN_PROGRESS.value,  # Re-opening
        ],
        TaskStatus.CANCELLED.value: [
            TaskStatus.PENDING.value,
        ],
    }

    # Valid assignment types
    VALID_ASSIGNMENT_TYPES = ["agent", "user"]

    def __init__(self, session: AsyncSession):
        """
        Initialize the task service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._task_repository = TaskRepository(session)
        self._agent_repository = AgentRepository(session)

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def create_task(
        self,
        project_id: UUID,
        title: str,
        description: str | None = None,
        room_id: UUID | None = None,
        priority: str | None = None,
        assigned_to: UUID | None = None,
        assigned_to_type: str | None = None,
        created_by: UUID | None = None,
        dependencies: list[UUID] | None = None,
        due_date: datetime | None = None,
    ) -> TaskDB:
        """
        Create a new task with validation.

        Args:
            project_id: Project UUID
            title: Task title
            description: Optional task description
            room_id: Optional associated chat room
            priority: Task priority (default: MEDIUM)
            assigned_to: Optional assignee UUID
            assigned_to_type: Optional assignee type ("agent" or "user")
            created_by: Creator user UUID
            dependencies: Optional list of dependency task IDs
            due_date: Optional due date

        Returns:
            Created task database model

        Raises:
            HTTPException: 400 if dependencies don't exist
            HTTPException: 400 if assignee doesn't exist
            HTTPException: 400 if assignment type is invalid
        """
        # Validate dependencies exist
        if dependencies:
            for dep_id in dependencies:
                dep_task = await self._task_repository.get_by_id(dep_id)
                if dep_task is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"의존 작업을 찾을 수 없습니다: {dep_id}",
                    )

        # Validate assignee if provided
        if assigned_to and assigned_to_type:
            if assigned_to_type not in self.VALID_ASSIGNMENT_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"잘못된 할당 유형입니다: {assigned_to_type}. "
                    f"허용된 유형: {', '.join(self.VALID_ASSIGNMENT_TYPES)}",
                )

            if assigned_to_type == "agent":
                agent_exists = await self._agent_repository.exists(assigned_to)
                if not agent_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"할당된 에이전트를 찾을 수 없습니다: {assigned_to}",
                    )
            # User validation would go here when user service is available

        # Map polymorphic assigned_to to specific fields
        user_assigned_to: UUID | None = None
        agent_assigned_to: UUID | None = None
        if assigned_to and assigned_to_type:
            if assigned_to_type == "agent":
                agent_assigned_to = assigned_to
            elif assigned_to_type == "user":
                user_assigned_to = assigned_to

        # Create task with default values
        task = TaskDB(
            id=uuid4(),
            project_id=project_id,
            room_id=room_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING.value,
            priority=priority or TaskPriority.MEDIUM.value,
            assigned_to=assigned_to,  # Legacy field for backward compatibility
            assigned_to_type=assigned_to_type,  # Legacy field for backward compatibility
            user_assigned_to=user_assigned_to,
            agent_assigned_to=agent_assigned_to,
            created_by=created_by or uuid4(),  # Fallback to random UUID
            dependencies=dependencies or [],
            started_at=None,
            completed_at=None,
            due_date=due_date,
            result=None,
        )

        self._session.add(task)
        await self._session.flush()

        return task

    async def get_task(self, task_id: UUID) -> TaskDB:
        """
        Get task by ID with related data.

        Args:
            task_id: Task UUID

        Returns:
            Task database model with relationships

        Raises:
            HTTPException: 404 if task not found
        """
        stmt = select(TaskDB).where(TaskDB.id == task_id)
        result = await self._session.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"작업을 찾을 수 없습니다: {task_id}",
            )

        return task

    async def get_task_with_dependencies(self, task_id: UUID) -> TaskDB:
        """
        Get task by ID with dependency chain populated.

        Args:
            task_id: Task UUID

        Returns:
            Task database model with dependency tasks

        Raises:
            HTTPException: 404 if task not found
        """
        task = await self.get_task(task_id)

        # Load dependency tasks
        if task.dependencies:
            dep_tasks = await self._task_repository.get_by_ids(task.dependencies)
            # Attach as a transient property for API responses
            task._dependency_tasks = dep_tasks  # type: ignore[attr-defined]

        return task

    async def list_tasks(
        self,
        project_id: UUID | None = None,
        room_id: UUID | None = None,
        status: str | None = None,
        assigned_to: UUID | None = None,
        priority: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TaskDB]:
        """
        List tasks with filters and pagination.

        Args:
            project_id: Filter by project
            room_id: Filter by chat room
            status: Filter by status
            assigned_to: Filter by assignee
            priority: Filter by priority
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of task database models
        """
        filters = {}
        if project_id:
            filters["project_id"] = project_id
        if room_id:
            filters["room_id"] = room_id
        if status:
            filters["status"] = status
        if assigned_to:
            filters["assigned_to"] = assigned_to
        if priority:
            filters["priority"] = priority

        tasks = await self._task_repository.list_all(
            limit=limit,
            offset=offset,
            order_by="created_at",
            descending=True,
            filters=filters if filters else None,
        )

        return list(tasks)

    async def update_task(
        self,
        task_id: UUID,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        due_date: datetime | None = None,
        result: dict | None = None,
    ) -> TaskDB:
        """
        Update task fields with partial update support.

        Args:
            task_id: Task UUID
            title: New title (optional)
            description: New description (optional)
            priority: New priority (optional)
            due_date: New due date (optional)
            result: Task result dictionary (optional)

        Returns:
            Updated task database model

        Raises:
            HTTPException: 404 if task not found
        """
        task = await self.get_task(task_id)

        # Update provided fields
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if due_date is not None:
            task.due_date = due_date
        if result is not None:
            task.result = result

        await self._session.flush()
        return task

    async def delete_task(self, task_id: UUID) -> None:
        """
        Delete a task after checking for dependent tasks.

        Args:
            task_id: Task UUID

        Raises:
            HTTPException: 404 if task not found
            HTTPException: 400 if other tasks depend on this task
        """
        # Check if other tasks depend on this one
        stmt = select(TaskDB).where(TaskDB.dependencies.contains([task_id]))
        result = await self._session.execute(stmt)
        dependent_tasks = result.scalars().all()

        if dependent_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이 작업을 삭제할 수 없습니다. "
                f"{len(dependent_tasks)}개의 다른 작업이 이 작업에 의존합니다.",
            )

        task = await self.get_task(task_id)
        await self._session.delete(task)
        await self._session.flush()

    # ========================================================================
    # Assignment Management
    # ========================================================================

    async def assign_task(
        self,
        task_id: UUID,
        assigned_to: UUID,
        assigned_to_type: str,
    ) -> TaskDB:
        """
        Assign task to an agent or user.

        Args:
            task_id: Task UUID
            assigned_to: Assignee UUID
            assigned_to_type: Type of assignee ("agent" or "user")

        Returns:
            Updated task database model

        Raises:
            HTTPException: 404 if task not found
            HTTPException: 400 if assignment type is invalid
            HTTPException: 400 if agent assignee doesn't exist
            HTTPException: 400 if agent is not available
        """
        task = await self.get_task(task_id)

        # Validate assignment type
        if assigned_to_type not in self.VALID_ASSIGNMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"잘못된 할당 유형입니다: {assigned_to_type}. "
                f"허용된 유형: {', '.join(self.VALID_ASSIGNMENT_TYPES)}",
            )

        # Validate agent availability if assigning to agent
        if assigned_to_type == "agent":
            agent = await self._agent_repository.get_by_id(assigned_to)
            if agent is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"할당된 에이전트를 찾을 수 없습니다: {assigned_to}",
                )

            if not agent.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"에이전트가 비활성화되어 있어 할당할 수 없습니다: {agent.name}",
                )

        # Update task assignment using polymorphic foreign keys
        if assigned_to_type == "agent":
            task.agent_assigned_to = assigned_to
            task.user_assigned_to = None
        elif assigned_to_type == "user":
            task.user_assigned_to = assigned_to
            task.agent_assigned_to = None

        # Update legacy fields for backward compatibility
        task.assigned_to = assigned_to
        task.assigned_to_type = assigned_to_type

        await self._session.flush()
        return task

    async def unassign_task(self, task_id: UUID) -> TaskDB:
        """
        Remove task assignment.

        Args:
            task_id: Task UUID

        Returns:
            Updated task database model

        Raises:
            HTTPException: 404 if task not found
        """
        task = await self.get_task(task_id)

        # Clear both specific assignment fields
        task.user_assigned_to = None
        task.agent_assigned_to = None

        # Clear legacy fields for backward compatibility
        task.assigned_to = None
        task.assigned_to_type = None

        await self._session.flush()
        return task

    # ========================================================================
    # Status Management
    # ========================================================================

    async def update_task_status(
        self,
        task_id: UUID,
        new_status: str,
    ) -> TaskDB:
        """
        Update task status with transition validation and auto-timestamps.

        Args:
            task_id: Task UUID
            new_status: New status value

        Returns:
            Updated task database model

        Raises:
            HTTPException: 404 if task not found
            HTTPException: 400 if status transition is invalid
        """
        task = await self.get_task(task_id)

        # Validate status transition
        current_status = task.status
        valid_transitions = self.VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"잘못된 상태 전환입니다: {current_status} -> {new_status}. "
                f"허용된 전환: {', '.join(valid_transitions)}",
            )

        # Auto-update timestamps based on status
        now = datetime.now(UTC)

        if (
            new_status == TaskStatus.IN_PROGRESS.value
            and current_status == TaskStatus.PENDING.value
        ):
            task.started_at = now
        elif new_status in (TaskStatus.REVIEW.value, TaskStatus.COMPLETED.value):
            if not task.started_at:
                task.started_at = now
            task.completed_at = now
        elif new_status == TaskStatus.PENDING.value:
            # Reset timestamps when going back to pending
            task.started_at = None
            task.completed_at = None

        task.status = new_status
        await self._session.flush()

        return task

    async def start_task(self, task_id: UUID) -> TaskDB:
        """
        Set task status to IN_PROGRESS.

        Args:
            task_id: Task UUID

        Returns:
            Updated task database model
        """
        return await self.update_task_status(task_id, TaskStatus.IN_PROGRESS.value)

    async def complete_task(self, task_id: UUID, result: dict | None = None) -> TaskDB:
        """
        Set task status to COMPLETED with optional result.

        Args:
            task_id: Task UUID
            result: Optional task result

        Returns:
            Updated task database model
        """
        if result:
            await self.update_task(task_id, result=result)

        return await self.update_task_status(task_id, TaskStatus.COMPLETED.value)

    async def cancel_task(self, task_id: UUID) -> TaskDB:
        """
        Set task status to CANCELLED.

        Args:
            task_id: Task UUID

        Returns:
            Updated task database model
        """
        return await self.update_task_status(task_id, TaskStatus.CANCELLED.value)

    async def block_task(self, task_id: UUID) -> TaskDB:
        """
        Set task status to BLOCKED.

        Args:
            task_id: Task UUID

        Returns:
            Updated task database model
        """
        return await self.update_task_status(task_id, TaskStatus.BLOCKED.value)

    # ========================================================================
    # Dependency Management
    # ========================================================================

    async def add_task_dependency(self, task_id: UUID, dependency_id: UUID) -> TaskDB:
        """
        Add a dependency to a task.

        Args:
            task_id: Task UUID
            dependency_id: Dependency task UUID

        Returns:
            Updated task database model

        Raises:
            HTTPException: 404 if task or dependency not found
            HTTPException: 400 if dependency would create circular reference
        """
        task = await self.get_task(task_id)
        dependency_task = await self._task_repository.get_by_id(dependency_id)

        if dependency_task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"의존 작업을 찾을 수 없습니다: {dependency_id}",
            )

        # Check for circular dependency
        if dependency_id in task.dependencies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"작업이 이미 이 의존성을 가지고 있습니다: {dependency_id}",
            )

        # Check if adding would create a circular reference
        # (simplified check - production would do full graph traversal)
        if dependency_task.dependencies and task_id in dependency_task.dependencies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="순환 의존성을 만들 수 없습니다.",
            )

        task.dependencies.append(dependency_id)
        await self._session.flush()

        return task

    async def remove_task_dependency(self, task_id: UUID, dependency_id: UUID) -> TaskDB:
        """
        Remove a dependency from a task.

        Args:
            task_id: Task UUID
            dependency_id: Dependency task UUID

        Returns:
            Updated task database model

        Raises:
            HTTPException: 404 if task not found
        """
        task = await self.get_task(task_id)

        if dependency_id not in task.dependencies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"작업이 이 의존성을 가지고 있지 않습니다: {dependency_id}",
            )

        task.dependencies.remove(dependency_id)
        await self._session.flush()

        return task

    # ========================================================================
    # Utility Methods
    # ========================================================================

    async def task_exists(self, task_id: UUID) -> bool:
        """
        Check if a task exists.

        Args:
            task_id: Task UUID

        Returns:
            True if task exists, False otherwise
        """
        return await self._task_repository.exists(task_id)

    async def get_tasks_by_ids(self, task_ids: list[UUID]) -> list[TaskDB]:
        """
        Get multiple tasks by their IDs.

        Args:
            task_ids: List of task UUIDs

        Returns:
            List of task database models
        """
        return await self._task_repository.get_by_ids(task_ids)

    async def count_tasks(
        self,
        project_id: UUID | None = None,
        room_id: UUID | None = None,
        status: str | None = None,
        assigned_to: UUID | None = None,
        priority: str | None = None,
    ) -> int:
        """
        Count tasks with optional filters.

        Args:
            project_id: Filter by project
            room_id: Filter by chat room
            status: Filter by status
            assigned_to: Filter by assignee
            priority: Filter by priority

        Returns:
            Count of matching tasks
        """
        filters = {}
        if project_id:
            filters["project_id"] = project_id
        if room_id:
            filters["room_id"] = room_id
        if status:
            filters["status"] = status
        if assigned_to:
            filters["assigned_to"] = assigned_to
        if priority:
            filters["priority"] = priority

        return await self._task_repository.count(filters if filters else None)

    async def get_overdue_tasks(self, project_id: UUID | None = None) -> list[TaskDB]:
        """
        Get all overdue tasks.

        Args:
            project_id: Optional project filter

        Returns:
            List of overdue task database models
        """
        now = datetime.now(UTC)

        # Query for tasks with due_date < now and status not completed/cancelled
        stmt = select(TaskDB).where(
            TaskDB.due_date < now,
            TaskDB.status.in_(
                [
                    TaskStatus.PENDING.value,
                    TaskStatus.IN_PROGRESS.value,
                    TaskStatus.BLOCKED.value,
                    TaskStatus.REVIEW.value,
                ]
            ),
        )

        if project_id:
            stmt = stmt.where(TaskDB.project_id == project_id)

        stmt = stmt.order_by(TaskDB.due_date)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_available_tasks_for_agent(
        self,
        agent_id: UUID,
        limit: int = 50,
    ) -> list[TaskDB]:
        """
        Get tasks available for an agent to work on.

        Args:
            agent_id: Agent UUID
            limit: Maximum number of results

        Returns:
            List of available task database models
        """
        # Get pending or blocked tasks assigned to this agent
        stmt = (
            select(TaskDB)
            .where(
                TaskDB.agent_assigned_to == agent_id,
                TaskDB.status.in_(
                    [
                        TaskStatus.PENDING.value,
                        TaskStatus.BLOCKED.value,
                    ]
                ),
            )
            .order_by(TaskDB.priority.desc(), TaskDB.created_at.asc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        tasks = list(result.scalars().all())

        # Filter out tasks with unmet dependencies
        available_tasks = []
        for task in tasks:
            can_start = True
            for dep_id in task.dependencies:
                dep_task = await self._task_repository.get_by_id(dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED.value:
                    can_start = False
                    break

            if can_start:
                available_tasks.append(task)

        return available_tasks


def get_task_service(session: AsyncSession) -> TaskService:
    """
    Get a task service instance.

    Args:
        session: SQLAlchemy async session

    Returns:
        TaskService instance
    """
    return TaskService(session)
