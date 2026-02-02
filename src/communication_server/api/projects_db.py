"""
Projects API endpoints with database persistence.

Provides REST API for project CRUD operations, agent assignment,
and project-based messaging with database-backed storage.
"""

from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.project import ProjectDB, ProjectStatus
from agent_comm_core.models.auth import User
from agent_comm_core.models.project_chat import (
    AgentAssignmentRequest,
    ProjectCreateRequest,
    ProjectMessage,
    ProjectMessageCreate,
    ProjectUpdateRequest,
)
from agent_comm_core.repositories import ProjectRepository
from communication_server.dependencies import get_db_session, get_project_repository
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


# =============================================================================
# Pydantic models for responses
# =============================================================================


class ProjectCreateResponseDB(BaseModel):
    """Response after creating a project."""

    id: str
    project_id: str
    name: str
    description: str | None
    status: str
    allow_cross_project: bool
    created_at: datetime
    updated_at: datetime


class ProjectInfoDB(BaseModel):
    """Public information about a project."""

    id: str
    project_id: str
    name: str
    description: str | None
    status: str
    allow_cross_project: bool
    created_at: datetime
    updated_at: datetime
    owner_id: str | None = None


class ProjectListItemDB(BaseModel):
    """Project information for list views."""

    id: str
    project_id: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectArchiveResponse(BaseModel):
    """Response for archive/restore operations."""

    message: str
    project_id: str
    status: str


# =============================================================================
# In-memory message storage (TODO: Move to persistent storage)
# =============================================================================

_project_messages: dict[str, list[ProjectMessage]] = defaultdict(list)
_project_chat_participants: dict[str, set[str]] = defaultdict(set)


# =============================================================================
# Helper functions
# =============================================================================


def get_agent_registry():
    """Get the agent registry instance."""
    from communication_server.services.agent_registry import get_agent_registry

    return get_agent_registry()


async def verify_project_ownership(
    project_db: ProjectDB,
    user: User,
) -> bool:
    """
    Verify that the user owns the project.

    Args:
        project_db: Project database model
        user: Authenticated user

    Returns:
        True if user is owner

    Raises:
        HTTPException: If user is not owner
    """
    if str(project_db.owner_id) != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this project",
        )
    return True


async def _broadcast_project_event(project_id: str, event: dict):
    """
    Broadcast a project-related event to all connected WebSocket clients.

    Args:
        project_id: Project ID
        event: Event data to broadcast
    """
    from communication_server.websocket.status_handler import get_status_handler

    try:
        status_handler = get_status_handler(None)
        await status_handler.broadcast_to_all(event)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to broadcast project event: {e}")


def project_db_to_info(project: ProjectDB) -> ProjectInfoDB:
    """Convert ProjectDB to ProjectInfoDB."""
    return ProjectInfoDB(
        id=str(project.id),
        project_id=project.project_id,
        name=project.name,
        description=project.description,
        status=project.status,
        allow_cross_project=project.allow_cross_project,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner_id=str(project.owner_id) if project.owner_id else None,
    )


# =============================================================================
# Project CRUD Endpoints (Database-backed)
# =============================================================================


@router.post("/", response_model=ProjectCreateResponseDB, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreateRequest,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new project with database persistence.

    Args:
        project_data: Project creation details
        user: Authenticated user (will be owner)
        project_repo: Project repository
        session: Database session

    Returns:
        Created project information

    Raises:
        HTTPException: If project_id already exists
    """
    try:
        # Check if project_id already exists
        existing = await project_repo.get_by_project_id(project_data.project_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with ID '{project_data.project_id}' already exists",
            )

        # Create project
        from uuid import UUID

        project = await project_repo.create(
            owner_id=UUID(user.id),
            project_id=project_data.project_id,
            name=project_data.name,
            description=project_data.description or "",
            status=ProjectStatus.ACTIVE,
        )

        await session.commit()
        await session.refresh(project)

        return ProjectCreateResponseDB(
            id=str(project.id),
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            status=project.status,
            allow_cross_project=project.allow_cross_project,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        ) from e


@router.get("/", response_model=list[ProjectListItemDB])
async def list_projects(
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    List all projects owned by the current user.

    Args:
        user: Authenticated user
        project_repo: Project repository

    Returns:
        List of user's projects
    """
    try:
        from uuid import UUID

        projects = await project_repo.list_by_owner(
            owner_id=UUID(user.id),
            limit=100,
            include_archived=False,
        )

        return [
            ProjectListItemDB(
                id=str(p.id),
                project_id=p.project_id,
                name=p.name,
                description=p.description,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            async for p in projects
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        ) from e


@router.get("/{project_id}", response_model=ProjectInfoDB)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    Get a specific project by ID (owner-only access).

    Args:
        project_id: Project identifier
        user: Authenticated user
        project_repo: Project repository

    Returns:
        Project information

    Raises:
        HTTPException: If project not found or access denied
    """
    project = await project_repo.get_by_project_id_with_owner(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Verify ownership
    await verify_project_ownership(project, user)

    return project_db_to_info(project)


@router.put("/{project_id}", response_model=ProjectInfoDB)
async def update_project(
    project_id: str,
    project_data: ProjectUpdateRequest,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing project (owner-only access).

    Args:
        project_id: Project identifier
        project_data: Updated project data
        user: Authenticated user
        project_repo: Project repository
        session: Database session

    Returns:
        Updated project information

    Raises:
        HTTPException: If project not found or access denied
    """
    try:
        # Get project
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Verify ownership
        await verify_project_ownership(project, user)

        # Update project
        updated = await project_repo.update(
            project_id=project.id,
            name=project_data.name,
            description=project_data.description,
            status=project_data.status,
        )

        await session.commit()
        await session.refresh(updated)

        return project_db_to_info(updated)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        ) from e


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    force: bool = Query(False, description="Force delete (not implemented)"),
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a project (soft delete, owner-only access).

    Args:
        project_id: Project identifier
        force: Force delete flag (not implemented)
        user: Authenticated user
        project_repo: Project repository
        session: Database session

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If project not found or access denied
    """
    try:
        # Get project
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Verify ownership
        await verify_project_ownership(project, user)

        # Soft delete the project
        success = await project_repo.delete(project.id, soft_delete=True)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await session.commit()

        # Clean up in-memory messages
        if project_id in _project_messages:
            del _project_messages[project_id]
        if project_id in _project_chat_participants:
            del _project_chat_participants[project_id]

        return {
            "message": f"Project '{project_id}' deleted successfully",
            "project_id": project_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        ) from e


# =============================================================================
# Archive/Restore Endpoints (NEW)
# =============================================================================


@router.post("/{project_id}/archive", response_model=ProjectArchiveResponse)
async def archive_project(
    project_id: str,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Archive a project (owner-only access).

    Archived projects are hidden from the default list but can be restored.

    Args:
        project_id: Project identifier
        user: Authenticated user
        project_repo: Project repository
        session: Database session

    Returns:
        Archive confirmation

    Raises:
        HTTPException: If project not found or access denied
    """
    try:
        # Get project
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Verify ownership
        await verify_project_ownership(project, user)

        # Archive the project
        archived = await project_repo.archive(project.id)

        if not archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await session.commit()
        await session.refresh(archived)

        # Broadcast event
        await _broadcast_project_event(
            project_id,
            {
                "type": "project_archived",
                "project_id": project_id,
                "data": {
                    "archived_by": user.username,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            },
        )

        return ProjectArchiveResponse(
            message=f"Project '{project_id}' archived successfully",
            project_id=project_id,
            status=archived.status,
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive project: {str(e)}",
        ) from e


@router.post("/{project_id}/restore", response_model=ProjectArchiveResponse)
async def restore_project(
    project_id: str,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Restore an archived project (owner-only access).

    Args:
        project_id: Project identifier
        user: Authenticated user
        project_repo: Project repository
        session: Database session

    Returns:
        Restore confirmation

    Raises:
        HTTPException: If project not found or access denied
    """
    try:
        # Get project
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Verify ownership
        await verify_project_ownership(project, user)

        # Restore the project
        restored = await project_repo.restore(project.id)

        if not restored:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await session.commit()
        await session.refresh(restored)

        # Broadcast event
        await _broadcast_project_event(
            project_id,
            {
                "type": "project_restored",
                "project_id": project_id,
                "data": {
                    "restored_by": user.username,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            },
        )

        return ProjectArchiveResponse(
            message=f"Project '{project_id}' restored successfully",
            project_id=project_id,
            status=restored.status,
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore project: {str(e)}",
        ) from e


# =============================================================================
# Agent Assignment Endpoints (Modified for DB)
# =============================================================================


@router.post("/{project_id}/agents", status_code=status.HTTP_201_CREATED)
async def assign_agent_to_project(
    project_id: str,
    assignment: AgentAssignmentRequest,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    Assign an agent to a project (owner-only access).

    Args:
        project_id: Target project
        assignment: Assignment details
        user: Authenticated user
        project_repo: Project repository

    Returns:
        Assignment confirmation

    Raises:
        HTTPException: If agent or project not found, or access denied
    """
    try:
        # Verify project exists and user owns it
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await verify_project_ownership(project, user)

        # Get the agent
        agent_registry = get_agent_registry()
        agent = await agent_registry.get_agent_by_display_id(assignment.agent_id)

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{assignment.agent_id}' not found",
            )

        # Update agent's project_id
        agent.project_id = project_id
        await project_repo.update(project.id)  # Update timestamp
        from agent_comm_core.db.database import db_session

        async with db_session() as session:
            await session.commit()

        # Broadcast WebSocket event
        await _broadcast_project_event(
            project_id,
            {
                "type": "agent_assignment_changed",
                "project_id": project_id,
                "data": {
                    "agent_id": assignment.agent_id,
                    "action": "assigned",
                    "role": assignment.role,
                    "assigned_by": user.username,
                },
            },
        )

        return {
            "message": f"Agent '{assignment.agent_id}' assigned to project '{project_id}'",
            "project_id": project_id,
            "agent_id": assignment.agent_id,
            "role": assignment.role,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign agent: {str(e)}",
        ) from e


@router.delete("/{project_id}/agents/{agent_id}")
async def unassign_agent_from_project(
    project_id: str,
    agent_id: str,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    Unassign an agent from a project (owner-only access).

    Args:
        project_id: Project identifier
        agent_id: Agent identifier
        user: Authenticated user
        project_repo: Project repository

    Returns:
        Unassignment confirmation

    Raises:
        HTTPException: If agent or project not found, or access denied
    """
    try:
        # Verify project exists and user owns it
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await verify_project_ownership(project, user)

        # Get the agent
        agent_registry = get_agent_registry()
        agent = await agent_registry.get_agent_by_display_id(agent_id)

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{agent_id}' not found",
            )

        # Verify agent is in this project
        if agent.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent_id}' is not assigned to project '{project_id}'",
            )

        # Clear agent's project_id
        agent.project_id = None
        await project_repo.update(project.id)  # Update timestamp
        from agent_comm_core.db.database import db_session

        async with db_session() as session:
            await session.commit()

        # Broadcast WebSocket event
        await _broadcast_project_event(
            project_id,
            {
                "type": "agent_assignment_changed",
                "project_id": project_id,
                "data": {
                    "agent_id": agent_id,
                    "action": "unassigned",
                    "assigned_by": user.username,
                },
            },
        )

        return {
            "message": f"Agent '{agent_id}' unassigned from project '{project_id}'",
            "project_id": project_id,
            "agent_id": agent_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unassign agent: {str(e)}",
        ) from e


# =============================================================================
# Project Chat Message Endpoints (Unchanged, but with ownership check)
# =============================================================================


@router.post(
    "/{project_id}/messages", response_model=ProjectMessage, status_code=status.HTTP_201_CREATED
)
async def send_project_message(
    project_id: str,
    message: ProjectMessageCreate,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    Send a message to a project chat room (owner-only access).

    Args:
        project_id: Target project
        message: Message content
        user: Authenticated user
        project_repo: Project repository

    Returns:
        Created message

    Raises:
        HTTPException: If project not found, inactive, or access denied
    """
    try:
        # Verify project exists and user owns it
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await verify_project_ownership(project, user)

        # Check if project is active
        if project.status != ProjectStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project '{project_id}' is not active",
            )

        # Create message
        new_message = ProjectMessage(
            project_id=project_id,
            from_agent=message.from_agent,
            content=message.content,
            message_type=message.message_type,
            in_reply_to=message.in_reply_to,
            metadata=message.metadata,
        )

        # Store message
        _project_messages[project_id].append(new_message)

        # Keep only last 1000 messages per project
        if len(_project_messages[project_id]) > 1000:
            _project_messages[project_id] = _project_messages[project_id][-1000:]

        # Broadcast WebSocket event
        await _broadcast_project_event(
            project_id,
            {
                "type": "project_message",
                "project_id": project_id,
                "data": {
                    "message_id": new_message.message_id,
                    "from_agent": new_message.from_agent,
                    "content": new_message.content,
                    "message_type": new_message.message_type,
                    "timestamp": new_message.timestamp.isoformat(),
                    "in_reply_to": new_message.in_reply_to,
                },
            },
        )

        return new_message

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        ) from e


@router.get("/{project_id}/messages")
async def get_project_messages(
    project_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of messages to retrieve"),
    before: str | None = Query(None, description="Cursor for pagination (message ID)"),
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    Get messages from a project chat room (owner-only access).

    Args:
        project_id: Project identifier
        limit: Number of messages to retrieve
        before: Pagination cursor (message ID)
        user: Authenticated user
        project_repo: Project repository

    Returns:
        List of messages with pagination info

    Raises:
        HTTPException: If project not found or access denied
    """
    try:
        # Verify project exists and user owns it
        project = await project_repo.get_by_project_id(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        await verify_project_ownership(project, user)

        # Get messages
        messages = _project_messages.get(project_id, [])

        # Apply pagination cursor
        if before:
            messages = [m for m in messages if m.message_id < before]

        # Get last N messages (most recent first)
        messages = messages[-limit:]
        messages.reverse()  # Return in reverse chronological order

        return {
            "project_id": project_id,
            "messages": [
                {
                    "message_id": m.message_id,
                    "from_agent": m.from_agent,
                    "content": m.content,
                    "message_type": m.message_type,
                    "timestamp": m.timestamp.isoformat(),
                    "in_reply_to": m.in_reply_to,
                    "reactions": m.reactions,
                    "metadata": m.metadata,
                }
                for m in messages
            ],
            "pagination": {
                "limit": limit,
                "has_more": len(_project_messages.get(project_id, [])) > limit,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        ) from e


# =============================================================================
# Legacy Endpoints (for backward compatibility)
# =============================================================================


@router.get("/{project_id}/agents")
async def get_project_agents(
    project_id: str,
    user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    """
    Get agents for a specific project (owner-only access).

    Args:
        project_id: Project ID
        user: Authenticated user
        project_repo: Project repository

    Returns:
        List of agents in the specified project

    Raises:
        HTTPException: If project not found or access denied
    """
    # Verify project exists and user owns it
    project = await project_repo.get_by_project_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    await verify_project_ownership(project, user)

    agent_registry = get_agent_registry()
    agents = await agent_registry.get_agents_by_project(project_id)

    return {
        "project_id": project_id,
        "agents": [
            {
                "agent_id": agent.agent_id,
                "full_id": agent.full_id,
                "nickname": agent.nickname,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "last_seen": agent.last_seen.isoformat(),
                "current_meeting": str(agent.current_meeting) if agent.current_meeting else None,
                "project_id": agent.project_id,
            }
            for agent in agents
        ],
    }
