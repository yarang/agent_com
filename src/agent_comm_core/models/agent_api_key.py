"""
Agent API Key Pydantic models for API serialization.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class KeyStatus(str, Enum):
    """Status of an API key."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CreatorType(str, Enum):
    """Type of entity that created the record."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class AgentApiKeyCreate(BaseModel):
    """Model for creating an agent API key."""

    agent_id: UUID = Field(..., description="Agent UUID")
    project_id: UUID = Field(..., description="Project UUID")
    capabilities: list[str] = Field(
        default_factory=lambda: ["communicate"],
        description="Agent capabilities",
    )
    expires_in_days: int | None = Field(
        None, ge=1, le=365, description="Expiration in days"
    )


class AgentApiKeyResponse(BaseModel):
    """Response model for agent API key."""

    id: UUID = Field(..., description="Key ID")
    key_id: str = Field(..., description="Human-readable key ID")
    agent_id: UUID = Field(..., description="Agent UUID")
    project_id: UUID = Field(..., description="Project UUID")
    capabilities: list[str] = Field(..., description="Agent capabilities")
    key_prefix: str = Field(..., description="Key prefix (for identification)")
    status: KeyStatus = Field(..., description="Key status")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    plain_key: str | None = Field(None, description="Plain key (only on creation)")

    model_config = {"from_attributes": True}


class AgentKeyValidationResult(BaseModel):
    """Result of API key validation."""

    valid: bool = Field(..., description="Whether the key is valid")
    reason: str = Field(..., description="Reason for validation result")
    agent_id: UUID | None = Field(None, description="Agent ID if valid")
    project_id: UUID | None = Field(None, description="Project ID if valid")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
