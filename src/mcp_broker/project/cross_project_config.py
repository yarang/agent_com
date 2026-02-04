"""
Cross-project configuration for MCP Broker Server.

This module provides the CrossProjectConfig class which manages
cross-project communication relationships, mutual consent tracking,
and permission rules.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from mcp_broker.core.logging import get_logger
from mcp_broker.models.project import CrossProjectPermission


class RelationshipStatus(BaseModel):
    """Status of a cross-project relationship.

    Attributes:
        status: Current status (pending, active, suspended, revoked)
        established_at: When relationship was established
        last_modified: When relationship was last modified
        initiator: Which project initiated the relationship
    """

    status: Literal["pending", "active", "suspended", "revoked"] = Field(
        default="pending",
        description="Current relationship status",
    )
    established_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When relationship was established",
    )
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When relationship was last modified",
    )
    initiator: str | None = Field(
        default=None,
        description="Project ID that initiated the relationship",
    )


class CrossProjectConfig(BaseModel):
    """Configuration for cross-project communication between two projects.

    This class manages:
    - Mutual consent tracking (both projects must opt-in)
    - Permission rules storage
    - Configuration validation

    Attributes:
        project_a: First project in the relationship
        project_b: Second project in the relationship
        status: Relationship status
        permissions_a_to_b: Permissions from A to B
        permissions_b_to_a: Permissions from B to A
        metadata: Additional relationship metadata
    """

    project_a: str = Field(
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        description="First project ID",
    )
    project_b: str = Field(
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        description="Second project ID",
    )
    status: RelationshipStatus = Field(
        default_factory=RelationshipStatus,
        description="Relationship status information",
    )
    permissions_a_to_b: CrossProjectPermission = Field(
        default_factory=lambda: CrossProjectPermission(target_project_id=""),
        description="Permissions from project A to B",
    )
    permissions_b_to_a: CrossProjectPermission = Field(
        default_factory=lambda: CrossProjectPermission(target_project_id=""),
        description="Permissions from project B to A",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional relationship metadata",
    )

    def model_post_init(self, __context: object) -> None:
        """Validate configuration after initialization.

        Ensures:
        - Projects are different
        - Permission target IDs match
        """
        if self.project_a == self.project_b:
            raise ValueError("Cannot create cross-project config with same project")

        # Update permission target IDs
        self.permissions_a_to_b.target_project_id = self.project_b
        self.permissions_b_to_a.target_project_id = self.project_a

    def is_active(self) -> bool:
        """Check if relationship is active.

        Returns:
            True if status is "active"
        """
        return self.status.status == "active"

    def can_communicate_a_to_b(self, protocol_name: str) -> bool:
        """Check if project A can send specified protocol to B.

        Args:
            protocol_name: Protocol to check

        Returns:
            True if communication is allowed
        """
        if not self.is_active():
            return False

        perms = self.permissions_a_to_b

        # Check protocol whitelist
        if perms.allowed_protocols and protocol_name not in perms.allowed_protocols:
            return False

        return True

    def can_communicate_b_to_a(self, protocol_name: str) -> bool:
        """Check if project B can send specified protocol to A.

        Args:
            protocol_name: Protocol to check

        Returns:
            True if communication is allowed
        """
        if not self.is_active():
            return False

        perms = self.permissions_b_to_a

        # Check protocol whitelist
        if perms.allowed_protocols and protocol_name not in perms.allowed_protocols:
            return False

        return True

    def activate(self, initiator: str) -> None:
        """Activate the relationship.

        Args:
            initiator: Project ID activating the relationship
        """
        self.status.status = "active"
        self.status.last_modified = datetime.now(UTC)
        if not self.status.initiator:
            self.status.initiator = initiator

        logger = get_logger(__name__)
        logger.info(
            f"Cross-project relationship activated: {self.project_a} <-> {self.project_b}",
            extra={
                "context": {
                    "project_a": self.project_a,
                    "project_b": self.project_b,
                    "initiator": initiator,
                }
            },
        )

    def suspend(self) -> None:
        """Suspend the relationship."""
        self.status.status = "suspended"
        self.status.last_modified = datetime.now(UTC)

        logger = get_logger(__name__)
        logger.info(
            f"Cross-project relationship suspended: {self.project_a} <-> {self.project_b}",
            extra={"context": {"project_a": self.project_a, "project_b": self.project_b}},
        )

    def revoke(self) -> None:
        """Revoke the relationship."""
        self.status.status = "revoked"
        self.status.last_modified = datetime.now(UTC)

        logger = get_logger(__name__)
        logger.info(
            f"Cross-project relationship revoked: {self.project_a} <-> {self.project_b}",
            extra={"context": {"project_a": self.project_a, "project_b": self.project_b}},
        )

    def get_rate_limit_a_to_b(self) -> int:
        """Get rate limit for A to B communication.

        Returns:
            Messages per minute (0 = unlimited)
        """
        return self.permissions_a_to_b.message_rate_limit

    def get_rate_limit_b_to_a(self) -> int:
        """Get rate limit for B to A communication.

        Returns:
            Messages per minute (0 = unlimited)
        """
        return self.permissions_b_to_a.message_rate_limit

    @classmethod
    def create_pair(cls, project_a: str, project_b: str) -> tuple["CrossProjectConfig", "CrossProjectConfig"]:
        """Create a pair of cross-project configs.

        Each project gets its own config object for the relationship.

        Args:
            project_a: First project ID
            project_b: Second project ID

        Returns:
            Tuple of (config_for_a, config_for_b)
        """
        config_a = cls(
            project_a=project_a,
            project_b=project_b,
            permissions_a_to_b=CrossProjectPermission(target_project_id=project_b),
            permissions_b_to_a=CrossProjectPermission(target_project_id=project_a),
        )

        # Swap for config_for_b (perspective is reversed)
        config_b = cls(
            project_a=project_b,
            project_b=project_a,
            permissions_a_to_b=CrossProjectPermission(target_project_id=project_a),
            permissions_b_to_a=CrossProjectPermission(target_project_id=project_b),
        )

        return (config_a, config_b)


class CrossProjectRelationshipManager:
    """Manager for cross-project relationships.

    This class handles:
    - Relationship creation and validation
    - Mutual consent tracking
    - Permission synchronization
    """

    def __init__(self) -> None:
        """Initialize the relationship manager."""
        self._relationships: dict[tuple[str, str], CrossProjectConfig] = {}

        logger = get_logger(__name__)
        logger.info("CrossProjectRelationshipManager initialized")

    def _get_key(self, project_a: str, project_b: str) -> tuple[str, str]:
        """Get canonical key for relationship lookup.

        Args:
            project_a: First project ID
            project_b: Second project ID

        Returns:
            Sorted tuple for consistent lookup
        """
        return tuple(sorted((project_a, project_b)))  # type: ignore

    def get_relationship(
        self, project_a: str, project_b: str
    ) -> CrossProjectConfig | None:
        """Get relationship between two projects.

        Args:
            project_a: First project ID
            project_b: Second project ID

        Returns:
            CrossProjectConfig if found, None otherwise
        """
        key = self._get_key(project_a, project_b)
        return self._relationships.get(key)

    def create_relationship(
        self,
        project_a: str,
        project_b: str,
        permissions_a_to_b: CrossProjectPermission | None = None,
        permissions_b_to_a: CrossProjectPermission | None = None,
    ) -> CrossProjectConfig:
        """Create a new cross-project relationship.

        Args:
            project_a: First project ID
            project_b: Second project ID
            permissions_a_to_b: Permissions from A to B
            permissions_b_to_a: Permissions from B to A

        Returns:
            Created CrossProjectConfig

        Raises:
            ValueError: If relationship already exists
        """
        key = self._get_key(project_a, project_b)

        if key in self._relationships:
            raise ValueError(f"Relationship already exists between {project_a} and {project_b}")

        config = CrossProjectConfig(
            project_a=project_a,
            project_b=project_b,
            permissions_a_to_b=permissions_a_to_b or CrossProjectPermission(
                target_project_id=project_b
            ),
            permissions_b_to_a=permissions_b_to_a or CrossProjectPermission(
                target_project_id=project_a
            ),
            status=RelationshipStatus(status="pending"),
        )

        self._relationships[key] = config

        logger = get_logger(__name__)
        logger.info(
            f"Cross-project relationship created: {project_a} <-> {project_b}",
            extra={"context": {"project_a": project_a, "project_b": project_b}},
        )

        return config

    def activate_relationship(self, project_a: str, project_b: str, initiator: str) -> bool:
        """Activate a pending relationship.

        Args:
            project_a: First project ID
            project_b: Second project ID
            initiator: Project activating the relationship

        Returns:
            True if activated successfully
        """
        config = self.get_relationship(project_a, project_b)
        if not config:
            return False

        config.activate(initiator)
        return True

    def list_relationships(self, project_id: str) -> list[CrossProjectConfig]:
        """List all relationships for a project.

        Args:
            project_id: Project ID to list relationships for

        Returns:
            List of CrossProjectConfig
        """
        result = []
        for config in self._relationships.values():
            if config.project_a == project_id or config.project_b == project_id:
                result.append(config)

        return result

    def delete_relationship(self, project_a: str, project_b: str) -> bool:
        """Delete a relationship.

        Args:
            project_a: First project ID
            project_b: Second project ID

        Returns:
            True if deleted, False if not found
        """
        key = self._get_key(project_a, project_b)

        if key in self._relationships:
            del self._relationships[key]

            logger = get_logger(__name__)
            logger.info(
                f"Cross-project relationship deleted: {project_a} <-> {project_b}",
                extra={"context": {"project_a": project_a, "project_b": project_b}},
            )

            return True

        return False
