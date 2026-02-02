"""
Audit log Pydantic models for API serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Types of audit actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_TOKEN_CREATE = "auth_token_create"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"
    AUTH_TOKEN_REVOKE = "auth_token_revoke"
    AUTH_KEY_CREATE = "auth_key_create"
    AUTH_KEY_REVOKE = "auth_key_revoke"
    PANIC = "panic"
    PERMISSION_DENIED = "permission_denied"
    SECURITY_ALERT = "security_alert"


class EntityType(str, Enum):
    """Types of entities for audit logs."""

    USER = "user"
    PROJECT = "project"
    AGENT_API_KEY = "agent_api_key"
    COMMUNICATION = "communication"
    MEETING = "meeting"
    DECISION = "decision"
    MESSAGE = "message"
    SYSTEM = "system"


class ActorType(str, Enum):
    """Types of actors for audit logs."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    ANONYMOUS = "anonymous"


class AuditLogCreate(BaseModel):
    """Model for creating an audit log entry."""

    action: str = Field(..., description="The action performed")
    entity_type: str = Field(..., description="Type of entity affected")
    entity_id: UUID | None = Field(None, description="ID of entity affected")
    project_id: UUID | None = Field(None, description="Project context")
    actor_type: str = Field(..., description="Type of actor (user/agent/system)")
    actor_id: UUID | None = Field(None, description="ID of actor")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client user agent")
    action_details: dict[str, Any] | None = Field(
        None, description="Additional details"
    )
    status: str = Field(default="success", description="Status of action")
    occurred_at: datetime | None = Field(None, description="When the action occurred")


class AuditLogFilter(BaseModel):
    """Model for filtering audit logs."""

    action: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    project_id: UUID | None = None
    actor_type: str | None = None
    actor_id: UUID | None = None
    status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int | None = Field(100, ge=1, le=1000)
    offset: int | None = Field(0, ge=0)


class AuditLogResponse(BaseModel):
    """Response model for audit log entries."""

    id: int = Field(..., description="Audit log ID")
    action: str = Field(..., description="The action performed")
    entity_type: str = Field(..., description="Type of entity affected")
    entity_id: UUID | None = Field(None, description="ID of entity affected")
    project_id: UUID | None = Field(None, description="Project context")
    actor_type: str = Field(..., description="Type of actor (user/agent/system)")
    actor_id: UUID | None = Field(None, description="ID of actor")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client user agent")
    action_details: dict[str, Any] | None = Field(
        None, description="Additional details"
    )
    status: str = Field(..., description="Status of action")
    occurred_at: datetime = Field(..., description="When the action occurred")

    model_config = {"from_attributes": True}
