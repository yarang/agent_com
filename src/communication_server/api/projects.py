"""
Projects API endpoints.

Provides REST API for querying projects and their associated agents.
"""

from fastapi import APIRouter, Depends

from agent_comm_core.repositories.base import CommunicationRepository, MeetingRepository
from communication_server.dependencies import get_communication_repository, get_meeting_repository
from communication_server.services.agent_registry import get_agent_registry
from communication_server.services.statistics import StatisticsService, get_statistics_service

router = APIRouter(prefix="/projects", tags=["projects"])


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


@router.get("/")
async def list_projects():
    """
    Get list of all projects with agent counts.

    Returns a list of projects with:
    - project_id: Project identifier
    - agent_count: Total number of agents in project
    - active_count: Number of online/active agents
    - is_online: Whether project has any active agents

    For agents without a project, returns a special entry with project_id "_none".
    """
    registry = get_agent_registry()
    project_counts = await registry.get_project_agent_counts()

    projects = []
    for project_id, counts in project_counts.items():
        # Display name for agents without project
        display_id = project_id if project_id != "_none" else None
        display_name = "All Agents" if project_id == "_none" else project_id

        projects.append(
            {
                "project_id": display_id,
                "name": display_name,
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
