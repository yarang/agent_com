"""
Pydantic schemas for Agent API requests and responses.

Provides validation and serialization for agent CRUD operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Agent Request Schemas
# ============================================================================


class AgentCreate(BaseModel):
    """Request model for creating a new agent.

    Fields:
        project_id: Project UUID for the agent
        name: Unique agent name within the project
        nickname: Display name (optional)
        agent_type: Type of agent (e.g., "generic", "mcp", "llm")
        capabilities: List of agent capabilities
        config: Optional agent configuration
    """

    project_id: UUID = Field(..., description="Project UUID for the agent")
    name: str = Field(
        ...,
        description="Unique agent name within the project",
        min_length=1,
        max_length=255,
    )
    nickname: str | None = Field(
        None,
        description="Display name for the agent",
        max_length=255,
    )
    agent_type: str = Field(
        default="generic",
        description="Type of agent (e.g., 'generic', 'mcp', 'llm')",
        max_length=100,
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of agent capabilities (e.g., ['communicate', 'create_meetings'])",
    )
    config: dict[str, Any] | None = Field(
        None,
        description="Optional agent configuration settings",
    )


class AgentUpdate(BaseModel):
    """Request model for updating an agent.

    All fields are optional to support partial updates.
    """

    nickname: str | None = Field(None, max_length=255)
    agent_type: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)
    capabilities: list[str] | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


# ============================================================================
# Agent Response Schemas
# ============================================================================


class AgentResponse(BaseModel):
    """Response model for agent data.

    Represents the complete agent state as returned from the API.
    """

    id: UUID = Field(..., description="Agent UUID")
    project_id: UUID = Field(..., description="Associated project UUID")
    name: str = Field(..., description="Unique agent name")
    nickname: str | None = Field(None, description="Display name")
    agent_type: str = Field(..., description="Type of agent")
    status: str = Field(..., description="Current agent status")
    capabilities: list[str] = Field(..., description="Agent capabilities")
    config: dict[str, Any] | None = Field(None, description="Agent configuration")
    is_active: bool = Field(..., description="Whether the agent is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


__all__ = [
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
]
