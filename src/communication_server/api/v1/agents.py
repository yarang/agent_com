"""
Agent Management API endpoints for multi-tenancy support.

Provides CRUD operations for agents with owner-centered permissions.
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_comm_core.db.models.agent_api_key import AgentApiKeyDB, CreatorType, KeyStatus
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.models.auth import User
from communication_server.security.authorization import Permission, require_permission
from communication_server.security.tokens import generate_agent_token, hash_api_token

router = APIRouter(prefix="/agents", tags=["Agents"])


# ============================================================================
# Request/Response Models
# ============================================================================


class AgentCreate(BaseModel):
    """Request model for creating an agent."""

    nickname: str = Field(..., description="Agent display name", min_length=1, max_length=100)
    project_id: UUID = Field(..., description="Project UUID to associate agent with")
    capabilities: list[str] = Field(
        default=["mcp"],
        description="List of agent capabilities",
    )


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""

    nickname: str | None = Field(None, min_length=1, max_length=100)
    capabilities: list[str] | None = None


class AgentResponse(BaseModel):
    """Response model for agent."""

    id: UUID = Field(..., description="Agent UUID")
    key_id: str = Field(..., description="Human-readable key identifier")
    project_id: UUID = Field(..., description="Project UUID")
    nickname: str = Field(..., description="Agent display name (derived from key_id)")
    capabilities: list[str] = Field(..., description="Agent capabilities")
    key_prefix: str = Field(..., description="Key prefix for identification")
    status: str = Field(..., description="Key status")
    created_by_type: str = Field(..., description="Type of creator")
    created_by_id: UUID = Field(..., description="Creator UUID")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class AgentTokenResponse(BaseModel):
    """Response model for agent token creation."""

    token: str = Field(..., description="API bearer token (shown once)")
    agent: AgentResponse = Field(..., description="Agent details")
    message: str = Field(default="Store this token securely. It will not be shown again.")


class AgentRotateResponse(BaseModel):
    """Response model for agent token rotation."""

    token: str = Field(..., description="New API bearer token")
    agent: AgentResponse = Field(..., description="Updated agent details")
    message: str = Field(default="Old token has been revoked. Store the new token securely.")


# ============================================================================
# Helper Functions
# ============================================================================


async def _verify_project_access(project_id: UUID, user_id: UUID, session) -> ProjectDB:
    """
    Verify that a user has access to a project.

    Args:
        project_id: Project UUID
        user_id: User UUID
        session: Database session

    Returns:
        ProjectDB instance

    Raises:
        HTTPException: If project not found or access denied
    """
    from sqlalchemy import select

    # Get project
    result = await session.execute(select(ProjectDB).where(ProjectDB.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check ownership or superuser
    if project.owner_id != user_id and user_id != project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    return project


def _agent_db_to_response(agent_db: AgentApiKeyDB) -> AgentResponse:
    """
    Convert AgentApiKeyDB to AgentResponse.

    Args:
        agent_db: Database model

    Returns:
        AgentResponse model
    """
    return AgentResponse(
        id=agent_db.agent_id,
        key_id=agent_db.key_id,
        project_id=agent_db.project_id,
        nickname=agent_db.key_id,
        capabilities=agent_db.capabilities,
        key_prefix=agent_db.key_prefix,
        status=agent_db.status.value,
        created_by_type=agent_db.created_by_type,
        created_by_id=agent_db.created_by_id,
        expires_at=agent_db.expires_at,
        created_at=agent_db.created_at,
        updated_at=agent_db.updated_at,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("", response_model=AgentTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """
    Create a new agent API token.

    Requires PROJECT_CREATE permission. The agent is associated with a project.

    Args:
        agent_data: Agent creation data
        current_user: Current authenticated user

    Returns:
        Created agent with token (shown only once)
    """
    from agent_comm_core.db.database import db_session
    from agent_comm_core.repositories import AgentApiKeyRepository

    async with db_session() as session:
        # Verify project access
        project = await _verify_project_access(agent_data.project_id, current_user.id, session)

        # Generate agent ID and token
        agent_id = uuid4()
        token = generate_agent_token(str(project.id), agent_data.nickname)
        hashed_token = hash_api_token(token)

        # Generate key_id
        key_id = f"{agent_data.nickname}_{agent_id.hex[:8]}"

        # Create agent API key
        repo = AgentApiKeyRepository(session)
        agent_db = await repo.create(
            project_id=project.id,
            agent_id=agent_id,
            key_id=key_id,
            api_key_hash=hashed_token,
            key_prefix=token[:20],
            capabilities=agent_data.capabilities,
            created_by_type=CreatorType.USER,
            created_by_id=current_user.id,
        )
        await session.commit()

        # Log audit
        from agent_comm_core.db.models.audit_log import ActorType, AuditAction, EntityType
        from agent_comm_core.services.audit_log import get_audit_log_service

        audit_service = get_audit_log_service(session)
        await audit_service.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.AGENT,
            entity_id=agent_id,
            project_id=project.id,
            actor_type=ActorType.USER,
            actor_id=current_user.id,
            action_details={
                "key_id": key_id,
                "nickname": agent_data.nickname,
                "capabilities": agent_data.capabilities,
            },
        )

        # Auto-register in AgentRegistry for dashboard display
        try:
            from communication_server.services.agent_registry import get_agent_registry

            registry = get_agent_registry()
            await registry.register_agent(
                full_id=str(agent_id),
                nickname=agent_data.nickname,
                capabilities=agent_data.capabilities,
                project_id=str(project.id),
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to auto-register agent in AgentRegistry: {e}"
            )

        return AgentTokenResponse(
            token=token,
            agent=_agent_db_to_response(agent_db),
            message="Store this token securely. It will not be shown again.",
        )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
    project_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List agents accessible to the current user.

    Requires PROJECT_READ permission. Can filter by project.

    Args:
        current_user: Current authenticated user
        project_id: Optional project UUID filter
        skip: Number of agents to skip
        limit: Maximum number of agents to return

    Returns:
        List of agents
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Build base query
        stmt = select(AgentApiKeyDB)

        # Filter by project access (owner-only)
        if not current_user.is_superuser:
            # Get user's project IDs
            project_stmt = select(ProjectDB.id).where(ProjectDB.owner_id == current_user.id)
            project_result = await session.execute(project_stmt)
            user_project_ids = [row[0] for row in project_result.fetchall()]

            stmt = stmt.where(AgentApiKeyDB.project_id.in_(user_project_ids))

        # Additional project filter
        if project_id:
            stmt = stmt.where(AgentApiKeyDB.project_id == project_id)

        stmt = stmt.order_by(AgentApiKeyDB.created_at.desc()).offset(skip).limit(limit)

        result = await session.execute(stmt)
        agents = result.scalars().all()

        return [_agent_db_to_response(agent) for agent in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
):
    """
    Get an agent by ID.

    Requires PROJECT_READ permission.

    Args:
        agent_id: Agent UUID
        current_user: Current authenticated user

    Returns:
        Agent details
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Get agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Check project access
        await _verify_project_access(agent.project_id, current_user.id, session)

        return _agent_db_to_response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Update an agent.

    Requires PROJECT_UPDATE permission and project ownership.

    Note: Cannot update the token directly. Use rotate endpoint for that.

    Args:
        agent_id: Agent UUID
        agent_data: Update data
        current_user: Current authenticated user

    Returns:
        Updated agent
    """
    from sqlalchemy import select, update

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Get agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Check project access
        await _verify_project_access(agent.project_id, current_user.id, session)

        # Build update values
        update_values: dict = {}
        if agent_data.nickname is not None:
            # Update key_id (nickname is stored in key_id)
            update_values["key_id"] = f"{agent_data.nickname}_{agent_id.hex[:8]}"
        if agent_data.capabilities is not None:
            update_values["capabilities"] = agent_data.capabilities

        if not update_values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        # Perform update
        await session.execute(
            update(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id).values(**update_values)
        )
        await session.commit()

        # Refresh and get updated agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        updated_agent = result.scalar_one()

        return _agent_db_to_response(updated_agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_DELETE))],
):
    """
    Delete an agent.

    Requires PROJECT_DELETE permission and project ownership.

    Args:
        agent_id: Agent UUID
        current_user: Current authenticated user
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Get agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Check project access
        await _verify_project_access(agent.project_id, current_user.id, session)

        # Unregister from AgentRegistry
        try:
            from communication_server.services.agent_registry import get_agent_registry

            registry = get_agent_registry()
            await registry.unregister_agent(str(agent_id))
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to unregister agent from AgentRegistry: {e}"
            )

        # Delete agent
        await session.delete(agent)
        await session.commit()


@router.post("/{agent_id}/revoke", response_model=AgentResponse)
async def revoke_agent_token(
    agent_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Revoke an agent's API token.

    Requires PROJECT_UPDATE permission and project ownership.
    The agent is marked as revoked but not deleted.

    Args:
        agent_id: Agent UUID
        current_user: Current authenticated user

    Returns:
        Updated agent with revoked status
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session
    from agent_comm_core.repositories import AgentApiKeyRepository

    async with db_session() as session:
        # Get agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Check project access
        await _verify_project_access(agent.project_id, current_user.id, session)

        # Revoke token
        repo = AgentApiKeyRepository(session)
        await repo.revoke(agent.id)
        await session.commit()

        # Refresh and get updated agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        updated_agent = result.scalar_one()

        return _agent_db_to_response(updated_agent)


@router.post("/{agent_id}/rotate", response_model=AgentRotateResponse)
async def rotate_agent_token(
    agent_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Rotate an agent's API token.

    Requires PROJECT_UPDATE permission and project ownership.
    Invalidates the old token and generates a new one.

    Args:
        agent_id: Agent UUID
        current_user: Current authenticated user

    Returns:
        New token and updated agent details
    """
    from sqlalchemy import select, update

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Get agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Check project access
        project = await _verify_project_access(agent.project_id, current_user.id, session)

        # Generate new token
        new_token = generate_agent_token(str(project.id), agent.key_id.split("_")[0])
        new_hashed_token = hash_api_token(new_token)

        # Update agent with new token
        await session.execute(
            update(AgentApiKeyDB)
            .where(AgentApiKeyDB.agent_id == agent_id)
            .values(
                api_key_hash=new_hashed_token,
                key_prefix=new_token[:20],
                status=KeyStatus.ACTIVE,  # Ensure status is active
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

        # Refresh and get updated agent
        result = await session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        updated_agent = result.scalar_one()

        return AgentRotateResponse(
            token=new_token,
            agent=_agent_db_to_response(updated_agent),
            message="Old token has been revoked. Store the new token securely.",
        )
