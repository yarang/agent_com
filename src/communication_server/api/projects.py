"""
Projects API endpoints.

Provides REST API for project CRUD operations, agent assignment,
and project-based messaging.
"""

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from agent_comm_core.models.auth import User
from agent_comm_core.models.project_chat import (
    AgentAssignmentRequest,
    ProjectCreateRequest,
    ProjectMessage,
    ProjectMessageCreate,
    ProjectUpdateRequest,
)
from agent_comm_core.repositories.base import CommunicationRepository, MeetingRepository
from communication_server.dependencies import (
    get_communication_repository,
    get_meeting_repository,
)
from communication_server.security.dependencies import get_current_user
from communication_server.services.agent_registry import get_agent_registry
from communication_server.services.statistics import StatisticsService, get_statistics_service

router = APIRouter(prefix="/projects", tags=["projects"])


# Pydantic models for responses
class ProjectCreateResponse(BaseModel):
    """Response after creating a project."""

    project_id: str
    name: str
    description: str
    tags: list[str]
    api_keys: list[dict]  # Only returned on creation
    created_at: datetime
    status: str


class ProjectInfo(BaseModel):
    """Public information about a project."""

    project_id: str
    name: str
    description: str
    tags: list[str]
    status: str
    created_at: datetime
    last_modified: datetime
    statistics: dict


def get_stats_service(
    comm_repo: CommunicationRepository = Depends(get_communication_repository),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
) -> StatisticsService:
    """
    Get statistics service with injected dependencies.

    Args:
        comm_repo: Communication repository
        meeting_repo: Meeting repository

    Returns:
        Statistics service instance
    """
    return get_statistics_service(comm_repo, meeting_repo)


def get_project_registry():
    """Get the project registry instance."""
    from mcp_broker.project.registry import ProjectRegistry

    return ProjectRegistry()


# In-memory message storage for project chat
# TODO: Move to persistent storage
_project_messages: dict[str, list[ProjectMessage]] = defaultdict(list)
_project_chat_participants: dict[str, set[str]] = defaultdict(set)


# ==================== Project CRUD Endpoints ====================


@router.post("", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreateRequest,
    user: User = Depends(get_current_user),
    registry=Depends(get_project_registry),
):
    """
    Create a new project with generated API keys.

    Args:
        project_data: Project creation details
        user: Authenticated user
        registry: Project registry

    Returns:
        Created project with API keys (only shown once)
    """
    try:
        project = await registry.create_project(
            project_id=project_data.project_id,
            name=project_data.name,
            description=project_data.description,
            tags=project_data.tags,
            owner=user.username,
        )

        # Return API keys (only shown on creation)
        api_keys = [
            {
                "key_id": key.key_id,
                "api_key": key.api_key,
                "created_at": key.created_at,
                "is_active": key.is_active,
            }
            for key in project.api_keys
        ]

        return ProjectCreateResponse(
            project_id=project.project_id,
            name=project.metadata.name,
            description=project.metadata.description,
            tags=project.metadata.tags,
            api_keys=api_keys,
            created_at=project.status.created_at,
            status=project.status.status,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        ) from e


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),  # noqa: ARG001
    registry=Depends(get_project_registry),
):
    """
    Get a specific project by ID.

    Args:
        project_id: Project identifier
        user: Authenticated user
        registry: Project registry

    Returns:
        Project information

    Raises:
        HTTPException: If project not found
    """
    project = await registry.get_project(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    return ProjectInfo(
        project_id=project.project_id,
        name=project.metadata.name,
        description=project.metadata.description,
        tags=project.metadata.tags,
        status=project.status.status,
        created_at=project.status.created_at,
        last_modified=project.status.last_modified,
        statistics={
            "session_count": project.statistics.session_count,
            "message_count": project.statistics.message_count,
            "protocol_count": project.statistics.protocol_count,
            "last_activity": project.statistics.last_activity,
        },
    )


@router.put("/{project_id}", response_model=ProjectInfo)
async def update_project(
    project_id: str,
    project_data: ProjectUpdateRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    registry=Depends(get_project_registry),
):
    """
    Update an existing project.

    Args:
        project_id: Project identifier
        project_data: Updated project data
        user: Authenticated user
        registry: Project registry

    Returns:
        Updated project information

    Raises:
        HTTPException: If project not found
    """
    try:
        project = await registry.update_project(
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            tags=project_data.tags,
        )

        # Handle status update separately
        if project_data.status:
            from copy import deepcopy

            old_status = project.status
            project.status = deepcopy(old_status)
            project.status.status = project_data.status  # type: ignore

        return ProjectInfo(
            project_id=project.project_id,
            name=project.metadata.name,
            description=project.metadata.description,
            tags=project.metadata.tags,
            status=project.status.status,
            created_at=project.status.created_at,
            last_modified=project.status.last_modified,
            statistics={
                "session_count": project.statistics.session_count,
                "message_count": project.statistics.message_count,
                "protocol_count": project.statistics.protocol_count,
                "last_activity": project.statistics.last_activity,
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        ) from e


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    force: bool = Query(False, description="Force delete (requires admin)"),
    user: User = Depends(get_current_user),  # noqa: ARG001
    registry=Depends(get_project_registry),
):
    """
    Delete a project.

    Args:
        project_id: Project identifier
        force: Force delete even with active sessions (admin only)
        user: Authenticated user
        registry: Project registry

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If project not found or has active sessions
    """
    try:
        if not force:
            # Check for active agents in this project
            agent_registry = get_agent_registry()
            agents = await agent_registry.get_agents_by_project(project_id)
            active_agents = [a for a in agents if a.status in ("online", "active")]

            if active_agents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete project with {len(active_agents)} active agents. Use force=true to override.",
                )

        success = await registry.delete_project(project_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Clean up messages
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        ) from e


# ==================== Original List Endpoint ====================


@router.get("")
@router.get("/")
async def list_projects(
    user: User = Depends(get_current_user),
    registry=Depends(get_project_registry),
):
    """
    Get list of all projects with agent counts.

    Returns all registered projects with:
    - project_id: Project identifier
    - name: Project name
    - description: Project description
    - agent_count: Total number of agents in project
    - active_count: Number of online/active agents
    - is_online: Whether project has any active agents

    Includes projects with 0 agents.
    """
    # Get all projects from ProjectRegistry
    all_projects = await registry.list_projects(include_inactive=False)

    # Get agent counts from agent registry
    agent_registry = get_agent_registry()
    project_counts = await agent_registry.get_project_agent_counts()

    # Build project list with combined data
    projects = []

    # Add "All Agents" entry first (for agents without project)
    none_counts = project_counts.get("_none", {"total": 0, "online": 0})
    projects.append(
        {
            "project_id": None,
            "name": "All Agents",
            "description": "",
            "agent_count": none_counts["total"],
            "active_count": none_counts["online"],
            "is_online": none_counts["online"] > 0,
        }
    )

    # Add all registered projects
    for project in all_projects:
        counts = project_counts.get(project.project_id, {"total": 0, "online": 0})
        projects.append(
            {
                "project_id": project.project_id,
                "name": project.metadata.name,
                "description": project.metadata.description,
                "agent_count": counts["total"],
                "active_count": counts["online"],
                "is_online": counts["online"] > 0,
            }
        )

    # Sort: All Agents first, then by name
    projects.sort(key=lambda p: (p["project_id"] is not None, p["name"]))

    return {"projects": projects}


@router.get("/{project_id}/agents")
async def get_project_agents(project_id: str):
    """
    Get agents for a specific project.

    Args:
        project_id: Project ID or "_none" for agents without a project

    Returns:
        List of agents in the specified project
    """
    registry = get_agent_registry()

    # Handle special case for agents without project
    pid = None if project_id == "_none" else project_id

    agents = await registry.get_agents_by_project(pid)

    return {
        "project_id": pid,
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


# ==================== Agent Assignment Endpoints ====================


@router.post("/{project_id}/agents", status_code=status.HTTP_201_CREATED)
async def assign_agent_to_project(
    project_id: str,
    assignment: AgentAssignmentRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
):
    """
    Assign an agent to a project.

    Args:
        project_id: Target project
        assignment: Assignment details
        user: Authenticated user

    Returns:
        Assignment confirmation

    Raises:
        HTTPException: If agent or project not found
    """
    try:
        agent_registry = get_agent_registry()

        # Get the agent
        agent = await agent_registry.get_agent_by_display_id(assignment.agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{assignment.agent_id}' not found",
            )

        # Verify project exists
        registry = get_project_registry()
        project = await registry.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Update agent's project_id
        agent.project_id = project_id
        await registry.update_statistics(project_id, session_count_delta=1)

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
    user: User = Depends(get_current_user),  # noqa: ARG001
):
    """
    Unassign an agent from a project.

    Args:
        project_id: Project identifier
        agent_id: Agent identifier
        user: Authenticated user

    Returns:
        Unassignment confirmation

    Raises:
        HTTPException: If agent or project not found
    """
    try:
        agent_registry = get_agent_registry()

        # Get the agent
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

        # Update statistics
        registry = get_project_registry()
        await registry.update_statistics(project_id, session_count_delta=-1)

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


# ==================== Project Chat Message Endpoints ====================


@router.post(
    "/{project_id}/messages", response_model=ProjectMessage, status_code=status.HTTP_201_CREATED
)
async def send_project_message(
    project_id: str,
    message: ProjectMessageCreate,
    user: User = Depends(get_current_user),  # noqa: ARG001
):
    """
    Send a message to a project chat room.

    Args:
        project_id: Target project
        message: Message content
        user: Authenticated user

    Returns:
        Created message

    Raises:
        HTTPException: If project not found
    """
    try:
        # Verify project exists
        registry = get_project_registry()
        project = await registry.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Check if project is active
        if not project.is_active():
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

        # Update project statistics
        await registry.update_statistics(project_id, message_count_delta=1)

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
    user: User = Depends(get_current_user),  # noqa: ARG001
):
    """
    Get messages from a project chat room.

    Args:
        project_id: Project identifier
        limit: Number of messages to retrieve
        before: Pagination cursor (message ID)
        user: Authenticated user

    Returns:
        List of messages with pagination info

    Raises:
        HTTPException: If project not found
    """
    try:
        # Verify project exists
        registry = get_project_registry()
        project = await registry.get_project(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

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


# ==================== WebSocket Broadcasting ====================


async def _broadcast_project_event(project_id: str, event: dict):
    """
    Broadcast a project-related event to all connected WebSocket clients.

    Args:
        project_id: Project ID
        event: Event data to broadcast
    """
    # Get the connection manager
    from communication_server.websocket.status_handler import get_status_handler

    try:
        status_handler = get_status_handler(None)
        await status_handler.broadcast_to_all(event)
    except Exception as e:
        # Log error but don't fail the request
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to broadcast project event: {e}")
