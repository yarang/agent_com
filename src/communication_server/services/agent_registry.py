"""
Agent Registry Service for tracking connected agents.

Maintains in-memory registry of all agents with their metadata,
status, and last activity timestamps.
"""

from datetime import datetime
from uuid import UUID

from agent_comm_core.models.status import AgentInfo, format_agent_display_id


class AgentRegistry:
    """
    Registry for tracking agent connections and metadata.

    Stores agent information in memory with periodic cleanup of
    inactive agents.
    """

    def __init__(self, inactive_timeout_seconds: int = 300) -> None:
        """
        Initialize the agent registry.

        Args:
            inactive_timeout_seconds: Seconds before marking agent as inactive
        """
        self._agents: dict[str, AgentInfo] = {}
        self._full_id_to_display_id: dict[str, str] = {}
        self._nickname_to_display_ids: dict[str, set[str]] = {}
        self._inactive_timeout_seconds = inactive_timeout_seconds

    async def register_agent(
        self, full_id: str, nickname: str, capabilities: list[str], project_id: str | None = None
    ) -> AgentInfo:
        """
        Register a new agent or update existing agent.

        Args:
            full_id: Full UUID of the agent
            nickname: Agent nickname
            capabilities: List of agent capabilities
            project_id: Optional project ID for grouping agents

        Returns:
            The registered agent info
        """
        display_id = format_agent_display_id(full_id, nickname)

        # Check if agent already exists
        if display_id in self._agents:
            # Update existing agent
            agent = self._agents[display_id]
            agent.nickname = nickname
            agent.capabilities = capabilities
            agent.project_id = project_id
            agent.status = AgentInfo.__fields__["status"].default  # ONLINE
            agent.last_seen = datetime.utcnow()
        else:
            # Create new agent
            agent = AgentInfo(
                agent_id=display_id,
                full_id=full_id,
                nickname=nickname,
                status="online",
                capabilities=capabilities,
                last_seen=datetime.utcnow(),
                project_id=project_id,
            )
            self._agents[display_id] = agent
            self._full_id_to_display_id[full_id] = display_id

        # Update nickname index
        if nickname not in self._nickname_to_display_ids:
            self._nickname_to_display_ids[nickname] = set()
        self._nickname_to_display_ids[nickname].add(display_id)

        return agent

    async def update_agent_status(
        self,
        full_id: str,
        status: str,
        current_meeting: UUID | None = None,
    ) -> AgentInfo | None:
        """
        Update agent status and activity timestamp.

        Args:
            full_id: Full UUID of the agent
            status: New status (online, offline, active, idle, error)
            current_meeting: Optional meeting ID if agent is in a meeting

        Returns:
            Updated agent info or None if agent not found
        """
        display_id = self._full_id_to_display_id.get(full_id)
        if not display_id:
            return None

        agent = self._agents.get(display_id)
        if not agent:
            return None

        from agent_comm_core.models.status import AgentStatus

        try:
            agent.status = AgentStatus(status)
        except ValueError:
            agent.status = AgentStatus.OFFLINE

        agent.last_seen = datetime.utcnow()
        if current_meeting is not None:
            agent.current_meeting = current_meeting

        return agent

    async def update_agent_activity(self, full_id: str) -> AgentInfo | None:
        """
        Update agent's last seen timestamp.

        Args:
            full_id: Full UUID of the agent

        Returns:
            Updated agent info or None if agent not found
        """
        display_id = self._full_id_to_display_id.get(full_id)
        if not display_id:
            return None

        agent = self._agents.get(display_id)
        if not agent:
            return None

        agent.last_seen = datetime.utcnow()
        return agent

    async def get_all_agents(self) -> list[AgentInfo]:
        """
        Get all registered agents.

        Returns:
            List of all agent info
        """
        return list(self._agents.values())

    async def get_agent_by_display_id(self, display_id: str) -> AgentInfo | None:
        """
        Get agent by display ID.

        Args:
            display_id: Display agent ID (Nickname + UUID suffix)

        Returns:
            Agent info or None if not found
        """
        return self._agents.get(display_id)

    async def get_agent_by_full_id(self, full_id: str) -> AgentInfo | None:
        """
        Get agent by full UUID.

        Args:
            full_id: Full UUID of the agent

        Returns:
            Agent info or None if not found
        """
        display_id = self._full_id_to_display_id.get(full_id)
        if not display_id:
            return None
        return self._agents.get(display_id)

    async def get_active_agents(self) -> list[AgentInfo]:
        """
        Get all currently active agents.

        Returns:
            List of active agent info
        """
        return [agent for agent in self._agents.values() if agent.status in ("online", "active")]

    async def unregister_agent(self, full_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            full_id: Full UUID of the agent

        Returns:
            True if agent was unregistered, False if not found
        """
        display_id = self._full_id_to_display_id.get(full_id)
        if not display_id:
            return False

        agent = self._agents.pop(display_id, None)
        if not agent:
            return False

        # Remove from indexes
        self._full_id_to_display_id.pop(full_id, None)
        if agent.nickname in self._nickname_to_display_ids:
            self._nickname_to_display_ids[agent.nickname].discard(display_id)
            if not self._nickname_to_display_ids[agent.nickname]:
                self._nickname_to_display_ids.pop(agent.nickname, None)

        return True

    async def cleanup_inactive_agents(self) -> int:
        """
        Mark inactive agents as offline based on timeout.

        Returns:
            Number of agents marked as inactive
        """
        from agent_comm_core.models.status import AgentStatus

        now = datetime.utcnow()
        inactive_count = 0

        for agent in self._agents.values():
            if agent.status in ("online", "active"):
                time_diff = (now - agent.last_seen).total_seconds()
                if time_diff > self._inactive_timeout_seconds:
                    agent.status = AgentStatus.OFFLINE
                    inactive_count += 1

        return inactive_count

    async def get_agent_count(self) -> dict[str, int]:
        """
        Get agent counts by status.

        Returns:
            Dictionary with counts for each status
        """
        counts = {"online": 0, "offline": 0, "active": 0, "idle": 0, "error": 0, "total": 0}

        for agent in self._agents.values():
            counts[agent.status] = counts.get(agent.status, 0) + 1
            counts["total"] += 1

        return counts

    async def get_agents_by_project(self, project_id: str | None) -> list[AgentInfo]:
        """
        Get agents filtered by project ID.

        Args:
            project_id: Project ID to filter by, or None for agents without a project

        Returns:
            List of agent info for the specified project
        """
        if project_id is None:
            return [agent for agent in self._agents.values() if agent.project_id is None]
        return [agent for agent in self._agents.values() if agent.project_id == project_id]

    async def get_project_agent_counts(self) -> dict[str, dict[str, int]]:
        """
        Get agent counts grouped by project.

        Returns:
            Dictionary mapping project_id to counts dict with 'total', 'online', 'active' keys
        """
        counts: dict[str, dict[str, int]] = {"_none": {"total": 0, "online": 0, "active": 0}}

        for agent in self._agents.values():
            project_key = agent.project_id if agent.project_id else "_none"

            if project_key not in counts:
                counts[project_key] = {"total": 0, "online": 0, "active": 0}

            counts[project_key]["total"] += 1

            if agent.status in ("online", "active"):
                counts[project_key]["online"] += 1
                if agent.status == "active":
                    counts[project_key]["active"] += 1

        return counts

    async def delete_agent(self, full_id: str) -> bool:
        """
        Delete an agent by full ID.

        Args:
            full_id: Full UUID of the agent

        Returns:
            True if agent was deleted, False if not found
        """
        display_id = self._full_id_to_display_id.get(full_id)
        if not display_id:
            return False

        agent = self._agents.pop(display_id, None)
        if not agent:
            return False

        # Remove from indexes
        self._full_id_to_display_id.pop(full_id, None)
        if agent.nickname in self._nickname_to_display_ids:
            self._nickname_to_display_ids[agent.nickname].discard(display_id)
            if not self._nickname_to_display_ids[agent.nickname]:
                self._nickname_to_display_ids.pop(agent.nickname, None)

        return True


# Global registry instance
_agent_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry instance.

    Returns:
        The global AgentRegistry instance
    """
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
