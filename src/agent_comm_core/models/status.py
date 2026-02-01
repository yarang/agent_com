"""
Status board models for agent tracking and statistics.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Status of an agent."""

    ONLINE = "online"
    OFFLINE = "offline"
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"


class AgentInfo(BaseModel):
    """Information about an agent."""

    agent_id: str = Field(..., description="Display agent ID (Nickname + UUID suffix)")
    full_id: str = Field(..., description="Full UUID of the agent")
    nickname: str = Field(..., description="Agent nickname")
    status: AgentStatus = Field(default=AgentStatus.OFFLINE, description="Current agent status")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity timestamp"
    )
    current_meeting: UUID | None = Field(default=None, description="Current meeting ID if active")
    project_id: str | None = Field(default=None, description="Associated project ID")

    model_config = {"from_attributes": True}


class AgentStats(BaseModel):
    """Statistics for a specific agent."""

    agent_id: str = Field(..., description="Display agent ID")
    messages_sent: int = Field(default=0, description="Number of messages sent")
    messages_received: int = Field(default=0, description="Number of messages received")
    meetings_created: int = Field(default=0, description="Number of meetings created")
    meetings_participated: int = Field(default=0, description="Number of meetings participated in")
    decisions_proposed: int = Field(default=0, description="Number of decisions proposed")
    last_activity: datetime | None = Field(default=None, description="Last activity timestamp")


class SystemStats(BaseModel):
    """System-wide statistics."""

    total_agents: int = Field(default=0, description="Total number of registered agents")
    active_agents: int = Field(default=0, description="Number of currently active agents")
    total_messages: int = Field(default=0, description="Total number of messages")
    total_meetings: int = Field(default=0, description="Total number of meetings")
    active_meetings: int = Field(default=0, description="Number of currently active meetings")
    decisions_made: int = Field(default=0, description="Total number of decisions made")
    pending_decisions: int = Field(default=0, description="Number of pending decisions")


class ActivityPatterns(BaseModel):
    """Activity patterns analysis."""

    activity_by_hour: list[int] = Field(
        default_factory=lambda: [0] * 24, description="Message count by hour (0-23)"
    )
    activity_by_day: dict[str, int] = Field(
        default_factory=dict,
        description="Message count by day of week (Monday-Sunday)",
    )
    top_agents: list[dict] = Field(default_factory=list, description="Top agents by message count")
    recent_events: list[dict] = Field(default_factory=list, description="Recent system events")


class MessageEvent(BaseModel):
    """A single message event for timeline."""

    timestamp: datetime = Field(..., description="Event timestamp")
    from_agent: str = Field(..., description="Source agent ID")
    to_agent: str | None = Field(default=None, description="Target agent ID")
    event_type: str = Field(..., description="Event type (message, meeting, decision)")
    description: str = Field(..., description="Event description")
    metadata: dict = Field(default_factory=dict, description="Additional event metadata")


class AgentRegistration(BaseModel):
    """Model for agent registration."""

    full_id: str = Field(..., description="Full UUID of the agent")
    nickname: str = Field(..., description="Agent nickname", min_length=1, max_length=100)
    capabilities: list[str] = Field(default_factory=list, description="List of agent capabilities")
    project_id: str | None = Field(default=None, description="Associated project ID")


def format_agent_display_id(full_id: str, nickname: str) -> str:
    """
    Format agent display ID as Nickname + UUID suffix.

    Args:
        full_id: Full UUID string
        nickname: Agent nickname

    Returns:
        Display ID in format @Nickname-{last-8-chars}
    """
    try:
        uuid_obj = UUID(full_id)
        # Get last 8 characters of the UUID (without hyphens)
        uuid_str = str(uuid_obj).replace("-", "")
        suffix = uuid_str[-8:]
        return f"@{nickname}-{suffix}"
    except (ValueError, AttributeError):
        # If full_id is not a valid UUID, use last 8 chars
        suffix = full_id[-8:] if len(full_id) >= 8 else full_id
        return f"@{nickname}-{suffix}"


__all__ = [
    "AgentStatus",
    "AgentInfo",
    "AgentStats",
    "SystemStats",
    "ActivityPatterns",
    "MessageEvent",
    "AgentRegistration",
    "format_agent_display_id",
]
