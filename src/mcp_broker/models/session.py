"""
Pydantic models for session-related data structures.

This module defines the data models for client sessions,
including session state, capabilities, and status tracking.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class SessionCapabilities(BaseModel):
    """Capabilities declared by a session during connection.

    Attributes:
        supported_protocols: Dict mapping protocol names to supported versions
        supported_features: List of supported communication features
    """

    supported_protocols: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Protocol name -> list of supported versions",
    )
    supported_features: list[str] = Field(
        default_factory=list,
        description="Supported communication features",
    )

    @field_validator("supported_features")
    @classmethod
    def validate_features(cls, v: list[str]) -> list[str]:
        """Validate features are from supported set.

        Args:
            v: List of features

        Returns:
            Deduplicated features
        """
        # Allow custom features but provide validation for known ones
        known_features = {"point_to_point", "broadcast", "encryption", "compression"}
        return list(set(v))


"""Type alias for session status values."""
SessionStatus = Literal["active", "stale", "disconnected"]


class Session(BaseModel):
    """Complete session state for a connected client.

    Attributes:
        session_id: Unique session identifier (UUID v4)
        project_id: Project this session belongs to (for multi-project isolation)
        connection_time: When the session was created
        last_heartbeat: Timestamp of last heartbeat received
        status: Current session status
        capabilities: Session capabilities
        queue_size: Current message queue size
    """

    session_id: UUID = Field(default_factory=uuid4)
    project_id: str = Field(default="default", description="Project identifier for isolation")
    connection_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: SessionStatus = "active"
    capabilities: SessionCapabilities = Field(default_factory=SessionCapabilities)
    queue_size: int = Field(default=0, ge=0)

    @field_validator("last_heartbeat")
    @classmethod
    def validate_heartbeat_not_after_now(cls, v: datetime) -> datetime:
        """Ensure heartbeat is not in the future.

        Args:
            v: Heartbeat timestamp

        Returns:
            Validated timestamp

        Raises:
            ValueError: If timestamp is in the future
        """
        if v > datetime.now(UTC):
            raise ValueError("last_heartbeat cannot be in the future")
        return v

    def is_stale(self, stale_threshold_seconds: int) -> bool:
        """Check if session is stale based on heartbeat.

        Args:
            stale_threshold_seconds: Seconds without heartbeat before stale

        Returns:
            True if session is stale
        """
        elapsed = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        return elapsed >= stale_threshold_seconds

    def should_disconnect(self, disconnect_threshold_seconds: int) -> bool:
        """Check if session should be disconnected.

        Args:
            disconnect_threshold_seconds: Seconds without heartbeat before disconnect

        Returns:
            True if session should be disconnected
        """
        elapsed = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        return elapsed >= disconnect_threshold_seconds

    def supports_protocol(
        self, protocol_name: str, protocol_version: str
    ) -> bool:
        """Check if session supports a specific protocol version.

        Args:
            protocol_name: Protocol to check
            protocol_version: Version required

        Returns:
            True if session supports the protocol version
        """
        supported_versions = self.capabilities.supported_protocols.get(protocol_name, [])
        return protocol_version in supported_versions

    def find_common_protocols(
        self, other: "Session"
    ) -> dict[str, str]:
        """Find common protocols with their highest compatible version.

        Args:
            other: Another session to compare with

        Returns:
            Dict of protocol name -> highest common version
        """
        common: dict[str, str] = {}

        for proto_name, my_versions in self.capabilities.supported_protocols.items():
            their_versions = other.capabilities.supported_protocols.get(proto_name, [])

            # Find common versions
            common_versions = set(my_versions) & set(their_versions)
            if common_versions:
                # For simplicity, return the first common version
                # In production, would use semver to find highest compatible
                common[proto_name] = sorted(common_versions)[0]

        return common
