"""
Agent API endpoints for AgentDB CRUD operations.

Provides REST API for managing agents with project-level authorization.
"""

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.database import db_session
from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/agents", tags=["Agents"])


# =============================================================================
# Database Session Dependency
# =============================================================================


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for database session."""
    async with db_session() as session:
        yield session


# =============================================================================
# Response Models
# ============================================================================


class PaginatedAgentResponse(BaseModel):
    """Paginated response for agent list."""

    items: list[AgentResponse]
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


async def _verify_agent_name_unique(project_id: UUID, name: str, session: AsyncSession) -> None:
    """
    Verify that agent name is unique within the project.

    Args:
        project_id: Project UUID
        name: Agent name
        session: Database session

    Raises:
        HTTPException: If agent name already exists
    """
    result = await session.execute(
        select(AgentDB).where(
            AgentDB.project_id == project_id,
            AgentDB.name == name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"프로젝트에 이미 '{name}' 이름의 에이전트가 존재합니다",  # Agent name already exists
        )


def _agent_db_to_response(agent_db: AgentDB) -> AgentResponse:
    """
    Convert AgentDB to AgentResponse.

    Args:
        agent_db: Database model

    Returns:
        AgentResponse model
    """
    return AgentResponse.model_validate(agent_db)


# ============================================================================
# Agent CRUD Endpoints
# ============================================================================


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new agent.

    Requires JWT authentication. The agent name must be unique within the project.

    Args:
        agent_data: Agent creation data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Created agent with id

    Raises:
        HTTPException: 404 if project not found
                        403 if no project access
                        409 if agent name exists
    """
    # Verify project access
    project = await _verify_project_access(agent_data.project_id, current_user, session)

    # Verify agent name is unique
    await _verify_agent_name_unique(project.id, agent_data.name, session)

    # Create agent
    agent = AgentDB(
        project_id=project.id,
        name=agent_data.name,
        nickname=agent_data.nickname,
        agent_type=agent_data.agent_type,
        capabilities=agent_data.capabilities,
        config=agent_data.config,
        status="offline",
        is_active=True,
    )

    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    return _agent_db_to_response(agent)


@router.get("", response_model=PaginatedAgentResponse)
async def list_agents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    project_id: UUID | None = None,
    status: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    List agents with pagination and filtering.

    Requires JWT authentication. Users can only see agents from their projects.

    Args:
        current_user: Current authenticated user
        session: Database session
        project_id: Optional project UUID filter
        status: Optional status filter
        is_active: Optional active state filter
        page: Page number (1-indexed)
        size: Page size (max 100)

    Returns:
        Paginated list of agents
    """
    # Build base query
    stmt = select(AgentDB)

    # Filter by project access (owner-only)
    if not current_user.is_superuser:
        # Get user's project IDs
        project_stmt = select(ProjectDB.id).where(ProjectDB.owner_id == current_user.id)
        project_result = await session.execute(project_stmt)
        user_project_ids = [row[0] for row in project_result.fetchall()]
        stmt = stmt.where(AgentDB.project_id.in_(user_project_ids))

    # Apply optional filters
    if project_id:
        stmt = stmt.where(AgentDB.project_id == project_id)
    if status:
        stmt = stmt.where(AgentDB.status == status)
    if is_active is not None:
        stmt = stmt.where(AgentDB.is_active == is_active)

    # Count total for pagination
    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination
    stmt = stmt.order_by(AgentDB.created_at.desc())
    stmt = stmt.offset((page - 1) * size).limit(size)

    result = await session.execute(stmt)
    agents = result.scalars().all()

    return PaginatedAgentResponse(
        items=[_agent_db_to_response(agent) for agent in agents],
        total=total,
        page=page,
        size=size,
        has_more=total > page * size,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get an agent by ID.

    Requires JWT authentication and project access.

    Args:
        agent_id: Agent UUID
        current_user: Current authenticated user
        session: Database session

    Returns:
        Agent details

    Raises:
        HTTPException: 404 if agent not found
                        403 if no project access
    """
    result = await session.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="에이전트를 찾을 수 없습니다",  # Agent not found
        )

    # Check project access
    await _verify_project_access(agent.project_id, current_user, session)

    return _agent_db_to_response(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an agent.

    Requires JWT authentication and project access. Supports partial updates.

    Args:
        agent_id: Agent UUID
        agent_data: Partial update data
        current_user: Current authenticated user
        session: Database session

    Returns:
        Updated agent

    Raises:
        HTTPException: 404 if agent not found
                        403 if no project access
    """
    result = await session.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="에이전트를 찾을 수 없습니다",  # Agent not found
        )

    # Check project access
    await _verify_project_access(agent.project_id, current_user, session)

    # Apply updates
    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await session.commit()
    await session.refresh(agent)

    return _agent_db_to_response(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an agent.

    Requires JWT authentication and project access.
    CASCADE deletes related records (API keys, participants).

    Args:
        agent_id: Agent UUID
        current_user: Current authenticated user
        session: Database session

    Raises:
        HTTPException: 404 if agent not found
                        403 if no project access
    """
    result = await session.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="에이전트를 찾을 수 없습니다",  # Agent not found
        )

    # Check project access
    await _verify_project_access(agent.project_id, current_user, session)

    # Delete agent (CASCADE will handle related records)
    await session.delete(agent)
    await session.commit()


__all__ = ["router"]
