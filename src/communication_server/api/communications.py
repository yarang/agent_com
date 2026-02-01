"""
API endpoints for communication logging.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.communication import Communication, CommunicationCreate
from agent_comm_core.models.auth import User, Agent
from agent_comm_core.services.communication import CommunicationService

from communication_server.dependencies import get_db_session, get_communication_service
from communication_server.repositories.communication import (
    SQLAlchemyCommunicationRepository,
)
from communication_server.security.dependencies import (
    get_current_user,
    get_current_agent,
    require_communicate_capability,
)


router = APIRouter(prefix="/communications", tags=["communications"])


@router.post("", response_model=Communication, status_code=status.HTTP_201_CREATED)
async def log_communication(
    data: CommunicationCreate,
    agent: Agent = Depends(require_communicate_capability),
    service: CommunicationService = Depends(get_communication_service),
) -> Communication:
    """
    Log a new communication between agents.

    Requires agent authentication with 'communicate' capability.

    Args:
        data: Communication creation data
        agent: Authenticated agent (injected)
        service: Communication service (injected)

    Returns:
        The created communication record
    """
    try:
        return await service.log_communication(
            from_agent=data.from_agent,
            to_agent=data.to_agent,
            message_type=data.message_type,
            content=data.content,
            direction=data.direction,
            correlation_id=data.correlation_id,
            metadata=data.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[Communication])
async def query_communications(
    from_agent: Optional[str] = Query(None, description="Filter by source agent"),
    to_agent: Optional[str] = Query(None, description="Filter by target agent"),
    correlation_id: Optional[UUID] = Query(None, description="Filter by correlation ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> list[Communication]:
    """
    Query communications with optional filters.

    Requires user authentication (dashboard access).

    Args:
        from_agent: Optional source agent filter
        to_agent: Optional target agent filter
        correlation_id: Optional correlation ID filter
        limit: Maximum number of results
        user: Authenticated user (injected)
        service: Communication service (injected)

    Returns:
        List of matching communications
    """
    return await service.get_communications(
        from_agent=from_agent,
        to_agent=to_agent,
        correlation_id=correlation_id,
        limit=limit,
    )


@router.get("/recent", response_model=list[Communication])
async def list_recent_communications(
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> list[Communication]:
    """
    List recent communications.

    Requires user authentication (dashboard access).

    Args:
        limit: Maximum number of results
        user: Authenticated user (injected)
        service: Communication service (injected)

    Returns:
        List of recent communications
    """
    return await service.list_recent(limit=limit)


@router.get("/{communication_id}", response_model=Communication)
async def get_communication(
    communication_id: UUID,
    user: User = Depends(get_current_user),
    service: CommunicationService = Depends(get_communication_service),
) -> Communication:
    """
    Get a specific communication by ID.

    Requires user authentication (dashboard access).

    Args:
        communication_id: Communication ID
        user: Authenticated user (injected)
        service: Communication service (injected)

    Returns:
        The communication record

    Raises:
        HTTPException: If communication not found
    """
    communication = await service.get_communication(communication_id)
    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Communication {communication_id} not found",
        )
    return communication
