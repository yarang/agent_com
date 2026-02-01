"""
Status Board API endpoints.

Provides REST API for querying agent status, statistics,
and activity patterns.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from agent_comm_core.models.status import (
    ActivityPatterns,
    AgentInfo,
    AgentRegistration,
    MessageEvent,
    SystemStats,
)
from agent_comm_core.repositories.base import CommunicationRepository, MeetingRepository
from communication_server.dependencies import get_communication_repository, get_meeting_repository
from communication_server.services.agent_registry import get_agent_registry
from communication_server.services.statistics import StatisticsService, get_statistics_service

router = APIRouter(prefix="/status", tags=["status"])


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


@router.get("/agents", response_model=dict)
async def get_all_agents(
    project_id: str | None = Query(None, description="Filter by project ID"),
) -> dict:
    """
    Get all registered agents with their current status.

    Optionally filters by project ID if provided.

    Returns a list of all agents including their display ID,
    nickname, status, capabilities, and last seen timestamp.
    """
    registry = get_agent_registry()

    # Filter by project if specified
    if project_id is not None:
        agents = await registry.get_agents_by_project(project_id)
    else:
        agents = await registry.get_all_agents()

    return {
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
        ]
    }


@router.post("/agents/register", response_model=AgentInfo)
async def register_agent(registration: AgentRegistration) -> AgentInfo:
    """
    Register a new agent or update existing agent registration.

    Args:
        registration: Agent registration data with full_id, nickname, capabilities, project_id

    Returns:
        The registered agent info
    """
    registry = get_agent_registry()
    agent = await registry.register_agent(
        full_id=registration.full_id,
        nickname=registration.nickname,
        capabilities=registration.capabilities,
        project_id=registration.project_id,
    )

    return agent


@router.get("/agents/{display_id}", response_model=dict)
async def get_agent_info(
    display_id: str,
    stats_service: StatisticsService = Depends(get_stats_service),
) -> dict:
    """
    Get detailed information about a specific agent.

    Args:
        display_id: Display agent ID (e.g., @FrontendExpert-ef123456)
        stats_service: Statistics service

    Returns:
        Detailed agent information including statistics
    """
    registry = get_agent_registry()
    agent = await registry.get_agent_by_display_id(display_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {display_id} not found",
        )

    # Get agent statistics
    agent_stats = await stats_service.get_agent_stats(agent.full_id)

    return {
        "agent": {
            "agent_id": agent.agent_id,
            "full_id": agent.full_id,
            "nickname": agent.nickname,
            "status": agent.status,
            "capabilities": agent.capabilities,
            "last_seen": agent.last_seen.isoformat(),
            "current_meeting": str(agent.current_meeting) if agent.current_meeting else None,
        },
        "statistics": {
            "messages_sent": agent_stats.messages_sent,
            "messages_received": agent_stats.messages_received,
            "meetings_created": agent_stats.meetings_created,
            "meetings_participated": agent_stats.meetings_participated,
            "decisions_proposed": agent_stats.decisions_proposed,
            "last_activity": (
                agent_stats.last_activity.isoformat() if agent_stats.last_activity else None
            ),
        },
    }


@router.put("/agents/{display_id}/status")
async def update_agent_status(
    display_id: str,
    status: str = Query(..., description="New status: online, offline, active, idle, error"),
    current_meeting: str | None = Query(None, description="Current meeting UUID if active"),
) -> dict:
    """
    Update agent status.

    Args:
        display_id: Display agent ID
        status: New status value
        current_meeting: Optional meeting UUID

    Returns:
        Updated agent info
    """
    from uuid import UUID

    registry = get_agent_registry()
    agent = await registry.get_agent_by_display_id(display_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {display_id} not found",
        )

    meeting_uuid = UUID(current_meeting) if current_meeting else None
    updated_agent = await registry.update_agent_status(agent.full_id, status, meeting_uuid)

    if not updated_agent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent status",
        )

    return {
        "agent_id": updated_agent.agent_id,
        "status": updated_agent.status,
        "last_seen": updated_agent.last_seen.isoformat(),
        "current_meeting": (
            str(updated_agent.current_meeting) if updated_agent.current_meeting else None
        ),
    }


@router.get("/statistics", response_model=SystemStats)
async def get_system_statistics(
    stats_service: StatisticsService = Depends(get_stats_service),
) -> SystemStats:
    """
    Get system-wide statistics.

    Returns totals for agents, messages, meetings, and decisions.
    """
    return await stats_service.get_system_stats()


@router.get("/activity", response_model=ActivityPatterns)
async def get_activity_patterns(
    agent_id: str | None = Query(None, description="Optional agent ID to filter by"),
    stats_service: StatisticsService = Depends(get_stats_service),
) -> ActivityPatterns:
    """
    Get activity patterns and recent timeline.

    Returns hourly and daily activity breakdowns, top agents,
    and recent system events.

    Args:
        agent_id: Optional agent full ID to filter patterns
        stats_service: Statistics service

    Returns:
        Activity patterns with timeline
    """
    return await stats_service.get_activity_patterns(agent_id)


@router.get("/timeline", response_model=list[MessageEvent])
async def get_message_timeline(
    limit: int = Query(100, description="Maximum number of events", ge=1, le=500),
    stats_service: StatisticsService = Depends(get_stats_service),
) -> list[MessageEvent]:
    """
    Get recent message events timeline.

    Returns recent communications and meetings ordered by timestamp.

    Args:
        limit: Maximum number of events to return
        stats_service: Statistics service

    Returns:
        List of message events
    """
    return await stats_service.get_message_timeline(limit=limit)


@router.post("/agents/{display_id}/heartbeat")
async def agent_heartbeat(display_id: str) -> dict:
    """
    Agent heartbeat endpoint to update last activity.

    Agents should call this periodically to maintain their online status.

    Args:
        display_id: Display agent ID

    Returns:
        Confirmation of heartbeat
    """
    registry = get_agent_registry()
    agent = await registry.get_agent_by_display_id(display_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {display_id} not found",
        )

    await registry.update_agent_activity(agent.full_id)

    return {
        "status": "ok",
        "agent_id": agent.agent_id,
        "last_seen": agent.last_seen.isoformat(),
    }


@router.delete("/agents/{display_id}")
async def unregister_agent(display_id: str) -> dict:
    """
    Unregister an agent from the registry.

    Args:
        display_id: Display agent ID

    Returns:
        Confirmation of unregistration
    """
    registry = get_agent_registry()
    agent = await registry.get_agent_by_display_id(display_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {display_id} not found",
        )

    success = await registry.unregister_agent(agent.full_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister agent",
        )

    return {"status": "ok", "message": f"Agent {display_id} unregistered"}


@router.get("/health")
async def status_health_check() -> dict:
    """
    Health check endpoint for status service.

    Returns the current status of the status board service.
    """
    registry = get_agent_registry()
    counts = await registry.get_agent_count()

    return {
        "status": "healthy",
        "service": "status-board",
        "agent_counts": counts,
    }
