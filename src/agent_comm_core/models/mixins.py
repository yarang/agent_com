"""
Reusable mixins for cross-cutting concerns in models and services.

This module provides mixins that can be composed into classes to add
common functionality without deep inheritance hierarchies.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID


class TimestampMixin:
    """Mixin for timestamp-related functionality.

    Provides common timestamp operations for entities that track
    creation and update times.
    """

    @property
    def age_seconds(self) -> int:
        """Get the age of this entity in seconds.

        Returns:
            Number of seconds since creation
        """
        if not hasattr(self, "created_at") or self.created_at is None:
            return 0
        delta = datetime.now(UTC) - self.created_at
        return int(delta.total_seconds())

    @property
    def is_recent(self, seconds: int = 3600) -> bool:
        """Check if this entity is recent.

        Args:
            seconds: Threshold in seconds (default: 1 hour)

        Returns:
            True if created within the threshold
        """
        return self.age_seconds < seconds

    @property
    def is_stale(self, seconds: int = 86400) -> bool:
        """Check if this entity is stale.

        Args:
            seconds: Threshold in seconds (default: 24 hours)

        Returns:
            True if not updated within the threshold
        """
        if not hasattr(self, "updated_at") or self.updated_at is None:
            return False
        delta = datetime.now(UTC) - self.updated_at
        return int(delta.total_seconds()) > seconds


class StatusMixin:
    """Mixin for status-related functionality.

    Provides common status operations for entities with status fields.
    """

    @property
    def is_active(self) -> bool:
        """Check if this entity is active.

        Returns:
            True if status indicates active state
        """
        if not hasattr(self, "status"):
            return False
        return str(self.status).lower() == "active"

    @property
    def is_pending(self) -> bool:
        """Check if this entity is pending.

        Returns:
            True if status indicates pending state
        """
        if not hasattr(self, "status"):
            return False
        return str(self.status).lower() == "pending"

    @property
    def is_completed(self) -> bool:
        """Check if this entity is completed.

        Returns:
            True if status indicates completed state
        """
        if not hasattr(self, "status"):
            return False
        status_lower = str(self.status).lower()
        return status_lower in ("completed", "closed", "done")

    @property
    def is_failed(self) -> bool:
        """Check if this entity has failed.

        Returns:
            True if status indicates failed state
        """
        if not hasattr(self, "status"):
            return False
        status_lower = str(self.status).lower()
        return status_lower in ("failed", "error", "cancelled", "revoked")


class OwnershipMixin:
    """Mixin for ownership-related functionality.

    Provides common ownership operations for entities owned by users.
    """

    def is_owned_by(self, user_id: UUID) -> bool:
        """Check if this entity is owned by the given user.

        Args:
            user_id: User UUID to check

        Returns:
            True if entity is owned by the user
        """
        if not hasattr(self, "owner_id") or self.owner_id is None:
            return False
        return self.owner_id == user_id

    def is_owned_by_agent(self, agent_id: UUID) -> bool:
        """Check if this entity is owned by the given agent.

        Args:
            agent_id: Agent UUID to check

        Returns:
            True if entity is owned by the agent
        """
        if not hasattr(self, "agent_id") or self.agent_id is None:
            return False
        return self.agent_id == agent_id


class MetadataMixin:
    """Mixin for metadata-related functionality.

    Provides common metadata operations for entities with metadata fields.
    """

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value by key.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        if not hasattr(self, "metadata") or self.metadata is None:
            return default
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value by key.

        Args:
            key: Metadata key
            value: Value to set
        """
        if not hasattr(self, "metadata"):
            self.metadata = {}
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def update_metadata(self, updates: dict[str, Any]) -> None:
        """Update multiple metadata values.

        Args:
            updates: Dictionary of key-value pairs to update
        """
        if not hasattr(self, "metadata"):
            self.metadata = {}
        if self.metadata is None:
            self.metadata = {}
        self.metadata.update(updates)

    def has_metadata(self, key: str) -> bool:
        """Check if metadata contains a key.

        Args:
            key: Metadata key to check

        Returns:
            True if key exists in metadata
        """
        if not hasattr(self, "metadata") or self.metadata is None:
            return False
        return key in self.metadata


class ValidationMixin:
    """Mixin for validation-related functionality.

    Provides common validation operations for entities.
    """

    def validate_required_fields(self, *fields: str) -> bool:
        """Validate that required fields are present and non-empty.

        Args:
            *fields: Field names to validate

        Returns:
            True if all required fields are present and non-empty

        Raises:
            ValueError: If any required field is missing or empty
        """
        for field in fields:
            if not hasattr(self, field):
                raise ValueError(f"Missing required field: {field}")
            value = getattr(self, field)
            if value is None or (isinstance(value, (str, list, dict)) and not value):
                raise ValueError(f"Required field cannot be empty: {field}")
        return True

    def validate_field_length(
        self, field: str, min_length: int = 0, max_length: int = 10000
    ) -> bool:
        """Validate field length.

        Args:
            field: Field name to validate
            min_length: Minimum length (default: 0)
            max_length: Maximum length (default: 10000)

        Returns:
            True if field length is within bounds

        Raises:
            ValueError: If field length is out of bounds
        """
        if not hasattr(self, field):
            raise ValueError(f"Missing field: {field}")
        value = getattr(self, field)
        if value is None:
            return True
        str_value = str(value)
        if len(str_value) < min_length:
            raise ValueError(
                f"Field '{field}' length {len(str_value)} is below minimum {min_length}"
            )
        if len(str_value) > max_length:
            raise ValueError(
                f"Field '{field}' length {len(str_value)} exceeds maximum {max_length}"
            )
        return True


class ExpirationMixin:
    """Mixin for expiration-related functionality.

    Provides common expiration operations for entities with expiration dates.
    """

    @property
    def is_expired(self) -> bool:
        """Check if this entity has expired.

        Returns:
            True if expiration date has passed
        """
        if not hasattr(self, "expires_at") or self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def expires_in_seconds(self) -> int | None:
        """Get seconds until expiration.

        Returns:
            Seconds until expiration, or None if no expiration
        """
        if not hasattr(self, "expires_at") or self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(UTC)
        return int(delta.total_seconds())

    @property
    def time_until_expiration(self) -> str:
        """Get human-readable time until expiration.

        Returns:
            Human-readable expiration time (e.g., "2 hours", "3 days")
        """
        seconds = self.expires_in_seconds
        if seconds is None:
            return "never"
        if seconds <= 0:
            return "expired"
        if seconds < 60:
            return f"{seconds} seconds"
        if seconds < 3600:
            return f"{seconds // 60} minutes"
        if seconds < 86400:
            return f"{seconds // 3600} hours"
        return f"{seconds // 86400} days"


__all__ = [
    "TimestampMixin",
    "StatusMixin",
    "OwnershipMixin",
    "MetadataMixin",
    "ValidationMixin",
    "ExpirationMixin",
]
