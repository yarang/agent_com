"""
Pydantic models for project-related data structures.

This module defines the data models for multi-project support,
including project definitions, API keys, metadata, and configuration.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from mcp_broker.models.protocol import ProtocolInfo


class ProjectAPIKey(BaseModel):
    """API key belonging to a project.

    Attributes:
        key_id: Unique identifier for this key
        api_key: The actual API key value
        created_at: When this key was created
        expires_at: Optional expiration timestamp
        is_active: Whether this key is currently active
    """

    key_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        description="Key identifier (e.g., 'default', 'admin')",
    )
    api_key: str = Field(
        min_length=32,
        description="API key value (format: {project_id}_{key_id}_{secret})",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    is_active: bool = True

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str) -> str:
        """Validate API key contains at least two underscores.

        Args:
            v: API key string

        Returns:
            Validated API key

        Raises:
            ValueError: If format is invalid
        """
        parts = v.split("_")
        if len(parts) < 3:
            raise ValueError(
                "API key must follow format: {project_id}_{key_id}_{secret}"
            )
        return v


class ProjectConfig(BaseModel):
    """Configuration settings for a project.

    Attributes:
        max_sessions: Maximum concurrent sessions allowed
        max_protocols: Maximum protocol versions allowed
        max_message_queue_size: Maximum messages per session queue
        allow_cross_project: Whether cross-project communication is allowed
        discoverable: Whether this project appears in discovery
        shared_protocols: List of protocol names to share read-only
    """

    max_sessions: int = Field(default=100, ge=1, description="Maximum concurrent sessions")
    max_protocols: int = Field(default=50, ge=1, description="Maximum protocol versions")
    max_message_queue_size: int = Field(default=100, ge=1, description="Max messages per queue")
    allow_cross_project: bool = Field(default=False, description="Allow cross-project communication")
    discoverable: bool = Field(default=True, description="Include in project discovery")
    shared_protocols: list[str] = Field(
        default_factory=list,
        description="Protocol names to share read-only",
    )


class CrossProjectPermission(BaseModel):
    """Permission for cross-project communication.

    Attributes:
        target_project_id: Project this permission applies to
        allowed_protocols: Whitelist of protocols that can be used
        message_rate_limit: Max messages per minute (0 = unlimited)
    """

    target_project_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        description="Target project for cross-project communication",
    )
    allowed_protocols: list[str] = Field(
        default_factory=list,
        description="Allowed protocol names for communication",
    )
    message_rate_limit: int = Field(default=0, ge=0, description="Messages per minute (0=unlimited)")


class ProjectMetadata(BaseModel):
    """Public metadata about a project.

    Attributes:
        name: Human-readable project name
        description: Optional project description
        tags: Searchable tags
        owner: Optional owner identifier
    """

    name: str = Field(min_length=1, max_length=100, description="Human-readable name")
    description: str = Field(default="", max_length=500, description="Project description")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    owner: str | None = Field(default=None, description="Project owner identifier")


class ProjectStatistics(BaseModel):
    """Usage statistics for a project.

    Attributes:
        session_count: Current number of active sessions
        message_count: Total messages sent (project lifetime)
        protocol_count: Number of registered protocols
        last_activity: Timestamp of last activity
    """

    session_count: int = Field(default=0, ge=0, description="Current active sessions")
    message_count: int = Field(default=0, ge=0, description="Total messages sent")
    protocol_count: int = Field(default=0, ge=0, description="Registered protocols")
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last activity timestamp",
    )


class ProjectStatus(BaseModel):
    """Status information for a project.

    Attributes:
        status: Current project status
        created_at: Project creation timestamp
        last_modified: Last modification timestamp
    """

    status: Literal["active", "inactive", "suspended"] = Field(
        default="active",
        description="Project status",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Project creation timestamp",
    )
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last modification timestamp",
    )


class ProjectDefinition(BaseModel):
    """Complete project definition with all configuration.

    Attributes:
        project_id: Unique project identifier (snake_case)
        metadata: Public project metadata
        api_keys: List of API keys for this project
        config: Project configuration
        cross_project_permissions: Cross-project communication rules
        statistics: Usage statistics
        status: Project status information
    """

    project_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        description="Unique project identifier (snake_case)",
    )
    metadata: ProjectMetadata = Field(
        default_factory=ProjectMetadata,
        description="Public project metadata",
    )
    api_keys: list[ProjectAPIKey] = Field(
        default_factory=list,
        description="Project API keys",
    )
    config: ProjectConfig = Field(
        default_factory=ProjectConfig,
        description="Project configuration",
    )
    cross_project_permissions: list[CrossProjectPermission] = Field(
        default_factory=list,
        description="Cross-project communication permissions",
    )
    statistics: ProjectStatistics = Field(
        default_factory=ProjectStatistics,
        description="Usage statistics",
    )
    status: ProjectStatus = Field(
        default_factory=ProjectStatus,
        description="Project status information",
    )

    @field_validator("project_id")
    @classmethod
    def validate_project_id_not_reserved(cls, v: str) -> str:
        """Validate project_id is not a reserved word.

        Args:
            v: Project ID to validate

        Returns:
            Validated project ID

        Raises:
            ValueError: If project_id is reserved
        """
        reserved = {"default", "system", "admin", "root"}
        if v.lower() in reserved:
            raise ValueError(
                f"Project ID '{v}' is reserved. "
                f"Reserved words: {', '.join(sorted(reserved))}"
            )
        return v

    @field_validator("api_keys")
    @classmethod
    def validate_has_api_keys(cls, v: list[ProjectAPIKey]) -> list[ProjectAPIKey]:
        """Validate project has at least one active API key.

        Args:
            v: List of API keys

        Returns:
            Validated API keys

        Raises:
            ValueError: If no active API keys
        """
        if not v:
            raise ValueError("Project must have at least one API key")
        return v

    def is_active(self) -> bool:
        """Check if project is currently active.

        Returns:
            True if project status is active
        """
        return self.status.status == "active"

    def has_active_api_key(self) -> bool:
        """Check if project has at least one active API key.

        Returns:
            True if at least one API key is active and not expired
        """
        now = datetime.now(UTC)
        return any(
            key.is_active and (key.expires_at is None or key.expires_at > now)
            for key in self.api_keys
        )

    def get_active_api_keys(self) -> list[ProjectAPIKey]:
        """Get all active, non-expired API keys.

        Returns:
            List of active API keys
        """
        now = datetime.now(UTC)
        return [
            key
            for key in self.api_keys
            if key.is_active and (key.expires_at is None or key.expires_at > now)
        ]


class ProjectInfo(BaseModel):
    """Public information about a project (for discovery).

    Attributes:
        project_id: Project identifier
        metadata: Public project metadata
        config_subset: Subset of configuration (safe to share)
        statistics: Usage statistics
        status: Current status
    """

    project_id: str
    metadata: ProjectMetadata
    config_subset: dict = Field(
        default_factory=dict,
        description="Subset of config safe for sharing",
    )
    statistics: ProjectStatistics
    status: Literal["active", "inactive", "suspended"]

    @classmethod
    def from_definition(cls, definition: ProjectDefinition) -> "ProjectInfo":
        """Create ProjectInfo from ProjectDefinition.

        Args:
            definition: Full project definition

        Returns:
            Public project information
        """
        return cls(
            project_id=definition.project_id,
            metadata=definition.metadata,
            config_subset={
                "allow_cross_project": definition.config.allow_cross_project,
                "discoverable": definition.config.discoverable,
                "shared_protocols": definition.config.shared_protocols,
            },
            statistics=definition.statistics,
            status=definition.status.status,
        )
