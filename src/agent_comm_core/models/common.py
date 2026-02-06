"""
Common enums and constants used across the agent communication system.

This module provides a single source of truth for all enumerations
to eliminate duplication and ensure consistency across models, services,
and repositories.
"""

from enum import Enum

# ============================================================================
# Actor/Creator Types
# ============================================================================


class ActorType(str, Enum):
    """Types of actors that can perform actions in the system.

    Used for audit logs, permissions, and tracking who performed actions.
    """

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    ANONYMOUS = "anonymous"


# Alias for backwards compatibility
CreatorType = ActorType


class SenderType(str, Enum):
    """Types of message senders in chat communication.

    Simplified version of ActorType specifically for chat messages.
    """

    USER = "user"
    AGENT = "agent"


# ============================================================================
# Common Status Values
# ============================================================================


class CommonStatus(str, Enum):
    """Common status values used across entities.

    Provides a standard set of statuses that can be reused across
    different entity types.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


# ============================================================================
# Project-Specific Status
# ============================================================================


class ProjectStatus(str, Enum):
    """Status of a project.

    Extends CommonStatus with project-specific values.
    """

    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"


# ============================================================================
# Agent Status
# ============================================================================


class AgentStatus(str, Enum):
    """Status of an agent.

    Represents the current operational state of an agent.
    """

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


# ============================================================================
# Task Status and Priority
# ============================================================================


class TaskStatus(str, Enum):
    """Status of a task.

    Tracks the lifecycle state of a task.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority levels for tasks.

    Indicates the urgency and importance of a task.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# API Key Status
# ============================================================================


class KeyStatus(str, Enum):
    """Status of an API key.

    Tracks the lifecycle of API keys.
    """

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


# ============================================================================
# Meeting Status
# ============================================================================


class MeetingStatus(str, Enum):
    """Status of a meeting.

    Tracks the lifecycle of agent coordination meetings.
    """

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================================
# Decision Status
# ============================================================================


class DecisionStatus(str, Enum):
    """Status of a decision.

    Tracks the lifecycle of agent decisions.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


# ============================================================================
# Communication Direction
# ============================================================================


class CommunicationDirection(str, Enum):
    """Direction of communication between agents.

    Used to track message flow patterns.
    """

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


# ============================================================================
# Message Types
# ============================================================================


class MessageType(str, Enum):
    """Types of chat messages.

    Categorizes different message types for handling and display.
    """

    TEXT = "text"
    SYSTEM = "system"
    FILE = "file"
    EMBEDDING = "embedding"


# ============================================================================
# Audit Actions
# ============================================================================


class AuditAction(str, Enum):
    """Types of audit actions for security logging.

    Categorizes all auditable events in the system.
    """

    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Authentication
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_TOKEN_CREATE = "auth_token_create"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"
    AUTH_TOKEN_REVOKE = "auth_token_revoke"
    AUTH_KEY_CREATE = "auth_key_create"
    AUTH_KEY_REVOKE = "auth_key_revoke"

    # Security events
    PANIC = "panic"
    PERMISSION_DENIED = "permission_denied"
    SECURITY_ALERT = "security_alert"


# ============================================================================
# Entity Types
# ============================================================================


class EntityType(str, Enum):
    """Types of entities for audit logging.

    Categorizes different entity types for tracking.
    """

    USER = "user"
    PROJECT = "project"
    AGENT = "agent"
    AGENT_API_KEY = "agent_api_key"
    TASK = "task"
    COMMUNICATION = "communication"
    MEETING = "meeting"
    DECISION = "decision"
    MESSAGE = "message"
    SYSTEM = "system"


# ============================================================================
# Common Constants
# ============================================================================

# Default limits
DEFAULT_LIST_LIMIT = 100
DEFAULT_LIST_OFFSET = 0
MAX_LIST_LIMIT = 1000

# Timestamp formats
TIMESTAMP_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S.%fZ"
TIMESTAMP_FORMAT_DATE = "%Y-%m-%d"
TIMESTAMP_FORMAT_DATETIME = "%Y-%m-%d %H:%M:%S"

# Validation constraints
MAX_STRING_LENGTH = 10000
MAX_TEXT_LENGTH = 100000
MIN_PASSWORD_LENGTH = 8


__all__ = [
    # Actor types
    "ActorType",
    "CreatorType",
    "SenderType",
    # Status enums
    "CommonStatus",
    "ProjectStatus",
    "AgentStatus",
    "TaskStatus",
    "TaskPriority",
    "KeyStatus",
    "MeetingStatus",
    "DecisionStatus",
    # Communication enums
    "CommunicationDirection",
    "MessageType",
    # Audit enums
    "AuditAction",
    "EntityType",
    # Constants
    "DEFAULT_LIST_LIMIT",
    "DEFAULT_LIST_OFFSET",
    "MAX_LIST_LIMIT",
    "TIMESTAMP_FORMAT_ISO",
    "TIMESTAMP_FORMAT_DATE",
    "TIMESTAMP_FORMAT_DATETIME",
    "MAX_STRING_LENGTH",
    "MAX_TEXT_LENGTH",
    "MIN_PASSWORD_LENGTH",
]
