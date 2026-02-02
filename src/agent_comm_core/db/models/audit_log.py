"""
Audit Log database model for immutable security event tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from agent_comm_core.db.base import Base


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


class AuditLogDB(Base):
    """
    Database model for immutable audit logging.

    Records all critical security actions for compliance and debugging.
    This table should be append-only with no updates allowed.
    """

    __tablename__ = "audit_logs"

    # Primary key (bigint for high-volume insert performance)
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement="auto",
    )

    # Action and entity details
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        default=None,
        index=True,
    )

    # Project context (for multi-tenancy)
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )

    # Actor details
    actor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        default=None,
        index=True,
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 can be up to 45 chars
        nullable=True,
        default=None,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Action details (JSONB for flexibility)
    action_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Result
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="success",
        index=True,
    )

    # Timestamp
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLogDB(id={self.id}, action={self.action}, "
            f"entity_type={self.entity_type}, actor_type={self.actor_type})>"
        )
