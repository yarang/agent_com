"""
Unit tests for base mixins.

Tests for reusable mixins that provide cross-cutting concerns.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest


class MockTimestampMixin:
    """Mock class for testing TimestampMixin."""

    def __init__(self, created_at: datetime | None = None, updated_at: datetime | None = None):
        self.created_at = created_at or datetime.now(UTC) - timedelta(seconds=100)
        self.updated_at = updated_at or datetime.now(UTC) - timedelta(seconds=50)


# Apply the mixin dynamically for testing
class TestableTimestamp(MockTimestampMixin):
    """Testable class with TimestampMixin applied."""

    from agent_comm_core.models.mixins import TimestampMixin


class MockStatusMixin:
    """Mock class for testing StatusMixin."""

    def __init__(self, status: str = "active"):
        self.status = status


# Apply the mixin dynamically for testing
class TestableStatus(MockStatusMixin):
    """Testable class with StatusMixin applied."""

    from agent_comm_core.models.mixins import StatusMixin


class MockOwnershipMixin:
    """Mock class for testing OwnershipMixin."""

    def __init__(self, owner_id: UUID | None = None, agent_id: UUID | None = None):
        self.owner_id = owner_id
        self.agent_id = agent_id


# Apply the mixin dynamically for testing
class TestableOwnership(MockOwnershipMixin):
    """Testable class with OwnershipMixin applied."""

    from agent_comm_core.models.mixins import OwnershipMixin


class MockMetadataMixin:
    """Mock class for testing MetadataMixin."""

    def __init__(self, metadata: dict | None = None):
        self.metadata = metadata


# Apply the mixin dynamically for testing
class TestableMetadata(MockMetadataMixin):
    """Testable class with MetadataMixin applied."""

    from agent_comm_core.models.mixins import MetadataMixin


class MockExpirationMixin:
    """Mock class for testing ExpirationMixin."""

    def __init__(self, expires_at: datetime | None = None):
        self.expires_at = expires_at


# Apply the mixin dynamically for testing
class TestableExpiration(MockExpirationMixin):
    """Testable class with ExpirationMixin applied."""

    from agent_comm_core.models.mixins import ExpirationMixin


class MockValidationMixin:
    """Mock class for testing ValidationMixin."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# Apply the mixin dynamically for testing
class TestableValidation(MockValidationMixin):
    """Testable class with ValidationMixin applied."""

    from agent_comm_core.models.mixins import ValidationMixin


# ============================================================================
# TimestampMixin Tests
# ============================================================================


class TestTimestampMixin:
    """Tests for TimestampMixin functionality."""

    def test_age_seconds_returns_correct_value(self):
        """Test that age_seconds returns the correct age in seconds."""
        obj = TestableTimestamp(created_at=datetime.now(UTC) - timedelta(seconds=123))
        assert obj.age_seconds == 123

    def test_age_returns_zero_when_created_at_is_none(self):
        """Test that age_seconds returns 0 when created_at is None."""
        obj = TestableTimestamp(created_at=None)
        assert obj.age_seconds == 0

    def test_age_returns_zero_when_created_at_missing(self):
        """Test that age_seconds returns 0 when created_at attribute is missing."""
        obj = TestableTimestamp.__new__(TestableTimestamp)
        assert obj.age_seconds == 0

    def test_is_recent_returns_true_for_recent_entity(self):
        """Test that is_recent returns True for recent entities."""
        obj = TestableTimestamp(created_at=datetime.now(UTC) - timedelta(seconds=500))
        assert obj.is_recent(seconds=1000) is True

    def test_is_recent_returns_false_for_old_entity(self):
        """Test that is_recent returns False for old entities."""
        obj = TestableTimestamp(created_at=datetime.now(UTC) - timedelta(seconds=5000))
        assert obj.is_recent(seconds=1000) is False

    def test_is_stale_returns_true_for_stale_entity(self):
        """Test that is_stale returns True for stale entities."""
        obj = TestableTimestamp(updated_at=datetime.now(UTC) - timedelta(seconds=100000))
        assert obj.is_stale(seconds=10000) is True

    def test_is_stale_returns_false_for_fresh_entity(self):
        """Test that is_stale returns False for fresh entities."""
        obj = TestableTimestamp(updated_at=datetime.now(UTC) - timedelta(seconds=100))
        assert obj.is_stale(seconds=10000) is False

    def test_is_stale_returns_false_when_updated_at_missing(self):
        """Test that is_stale returns False when updated_at attribute is missing."""
        obj = TestableTimestamp.__new__(TestableTimestamp)
        assert obj.is_stale(seconds=10000) is False


# ============================================================================
# StatusMixin Tests
# ============================================================================


class TestStatusMixin:
    """Tests for StatusMixin functionality."""

    def test_is_active_returns_true_for_active_status(self):
        """Test that is_active returns True for active status."""
        obj = TestableStatus(status="active")
        assert obj.is_active is True

    def test_is_active_returns_true_for_active_uppercase(self):
        """Test that is_active handles uppercase status."""
        obj = TestableStatus(status="ACTIVE")
        assert obj.is_active is True

    def test_is_active_returns_false_for_inactive_status(self):
        """Test that is_active returns False for inactive status."""
        obj = TestableStatus(status="inactive")
        assert obj.is_active is False

    def test_is_active_returns_false_when_status_missing(self):
        """Test that is_active returns False when status attribute is missing."""
        obj = TestableStatus.__new__(TestableStatus)
        assert obj.is_active is False

    def test_is_pending_returns_true_for_pending_status(self):
        """Test that is_pending returns True for pending status."""
        obj = TestableStatus(status="pending")
        assert obj.is_pending is True

    def test_is_completed_returns_true_for_completed_status(self):
        """Test that is_completed returns True for completed status."""
        obj = TestableStatus(status="completed")
        assert obj.is_completed is True

    def test_is_completed_returns_true_for_closed_status(self):
        """Test that is_completed returns True for closed status."""
        obj = TestableStatus(status="closed")
        assert obj.is_completed is True

    def test_is_completed_returns_true_for_done_status(self):
        """Test that is_completed returns True for done status."""
        obj = TestableStatus(status="done")
        assert obj.is_completed is True

    def test_is_failed_returns_true_for_failed_status(self):
        """Test that is_failed returns True for failed status."""
        obj = TestableStatus(status="failed")
        assert obj.is_failed is True

    def test_is_failed_returns_true_for_cancelled_status(self):
        """Test that is_failed returns True for cancelled status."""
        obj = TestableStatus(status="cancelled")
        assert obj.is_failed is True


# ============================================================================
# OwnershipMixin Tests
# ============================================================================


class TestOwnershipMixin:
    """Tests for OwnershipMixin functionality."""

    def test_is_owned_by_returns_true_for_matching_owner(self):
        """Test that is_owned_by returns True for matching owner."""
        owner_id = uuid4()
        obj = TestableOwnership(owner_id=owner_id)
        assert obj.is_owned_by(owner_id) is True

    def test_is_owned_by_returns_false_for_different_owner(self):
        """Test that is_owned_by returns False for different owner."""
        obj = TestableOwnership(owner_id=uuid4())
        assert obj.is_owned_by(uuid4()) is False

    def test_is_owned_by_returns_false_when_owner_id_missing(self):
        """Test that is_owned_by returns False when owner_id is None."""
        obj = TestableOwnership(owner_id=None)
        assert obj.is_owned_by(uuid4()) is False

    def test_is_owned_by_returns_false_when_owner_id_missing(self):
        """Test that is_owned_by returns False when owner_id attribute is missing."""
        obj = TestableOwnership.__new__(TestableOwnership)
        assert obj.is_owned_by(uuid4()) is False

    def test_is_owned_by_agent_returns_true_for_matching_agent(self):
        """Test that is_owned_by_agent returns True for matching agent."""
        agent_id = uuid4()
        obj = TestableOwnership(agent_id=agent_id)
        assert obj.is_owned_by_agent(agent_id) is True

    def test_is_owned_by_agent_returns_false_for_different_agent(self):
        """Test that is_owned_by_agent returns False for different agent."""
        obj = TestableOwnership(agent_id=uuid4())
        assert obj.is_owned_by_agent(uuid4()) is False


# ============================================================================
# MetadataMixin Tests
# ============================================================================


class TestMetadataMixin:
    """Tests for MetadataMixin functionality."""

    def test_get_metadata_returns_value_for_existing_key(self):
        """Test that get_metadata returns value for existing key."""
        obj = TestableMetadata(metadata={"key1": "value1", "key2": "value2"})
        assert obj.get_metadata("key1") == "value1"

    def test_get_metadata_returns_default_for_missing_key(self):
        """Test that get_metadata returns default for missing key."""
        obj = TestableMetadata(metadata={"key1": "value1"})
        assert obj.get_metadata("missing", "default") == "default"

    def test_get_metadata_returns_none_when_metadata_missing(self):
        """Test that get_metadata returns None when metadata is None."""
        obj = TestableMetadata(metadata=None)
        assert obj.get_metadata("key", "default") == "default"

    def test_set_metadata_sets_value(self):
        """Test that set_metadata sets a value."""
        obj = TestableMetadata(metadata={})
        obj.set_metadata("key1", "value1")
        assert obj.metadata["key1"] == "value1"

    def test_set_metadata_creates_metadata_if_none(self):
        """Test that set_metadata creates metadata dict if None."""
        obj = TestableMetadata(metadata=None)
        obj.set_metadata("key1", "value1")
        assert obj.metadata["key1"] == "value1"

    def test_update_metadata_updates_multiple_values(self):
        """Test that update_metadata updates multiple values."""
        obj = TestableMetadata(metadata={"key1": "value1"})
        obj.update_metadata({"key2": "value2", "key3": "value3"})
        assert obj.metadata == {"key1": "value1", "key2": "value2", "key3": "value3"}

    def test_has_metadata_returns_true_for_existing_key(self):
        """Test that has_metadata returns True for existing key."""
        obj = TestableMetadata(metadata={"key1": "value1"})
        assert obj.has_metadata("key1") is True

    def test_has_metadata_returns_false_for_missing_key(self):
        """Test that has_metadata returns False for missing key."""
        obj = TestableMetadata(metadata={"key1": "value1"})
        assert obj.has_metadata("missing") is False

    def test_has_metadata_returns_false_when_metadata_none(self):
        """Test that has_metadata returns False when metadata is None."""
        obj = TestableMetadata(metadata=None)
        assert obj.has_metadata("key") is False


# ============================================================================
# ExpirationMixin Tests
# ============================================================================


class TestExpirationMixin:
    """Tests for ExpirationMixin functionality."""

    def test_is_expired_returns_true_for_expired_entity(self):
        """Test that is_expired returns True for expired entities."""
        obj = TestableExpiration(expires_at=datetime.now(UTC) - timedelta(seconds=100))
        assert obj.is_expired is True

    def test_is_expired_returns_false_for_future_entity(self):
        """Test that is_expired returns False for future entities."""
        obj = TestableExpiration(expires_at=datetime.now(UTC) + timedelta(seconds=100))
        assert obj.is_expired is False

    def test_is_expired_returns_false_when_no_expiration(self):
        """Test that is_expired returns False when expires_at is None."""
        obj = TestableExpiration(expires_at=None)
        assert obj.is_expired is False

    def test_expires_in_seconds_returns_seconds_until_expiration(self):
        """Test that expires_in_seconds returns correct seconds."""
        obj = TestableExpiration(expires_at=datetime.now(UTC) + timedelta(seconds=500))
        assert obj.expires_in_seconds == 500

    def test_expires_in_seconds_returns_none_when_no_expiration(self):
        """Test that expires_in_seconds returns None when no expiration."""
        obj = TestableExpiration(expires_at=None)
        assert obj.expires_in_seconds is None

    def test_time_until_expiration_returns_human_readable_format(self):
        """Test that time_until_expiration returns human-readable format."""
        obj = TestableExpiration(expires_at=datetime.now(UTC) + timedelta(seconds=5000))
        result = obj.time_until_expiration
        assert result == "1 hours"

    def test_time_until_expiration_returns_expired_for_past(self):
        """Test that time_until_expiration returns 'expired' for past."""
        obj = TestableExpiration(expires_at=datetime.now(UTC) - timedelta(seconds=100))
        assert obj.time_until_expiration == "expired"

    def test_time_until_expiration_returns_never_for_none(self):
        """Test that time_until_expiration returns 'never' for None."""
        obj = TestableExpiration(expires_at=None)
        assert obj.time_until_expiration == "never"


# ============================================================================
# ValidationMixin Tests
# ============================================================================


class TestValidationMixin:
    """Tests for ValidationMixin functionality."""

    def test_validate_required_fields_passes_when_all_present(self):
        """Test that validate_required_fields passes when all fields present."""
        obj = TestableValidation(field1="value1", field2="value2")
        assert obj.validate_required_fields("field1", "field2") is True

    def test_validate_required_fields_raises_for_missing_field(self):
        """Test that validate_required_fields raises for missing field."""
        obj = TestableValidation(field1="value1")
        with pytest.raises(ValueError, match="Missing required field"):
            obj.validate_required_fields("field1", "field2")

    def test_validate_required_fields_raises_for_empty_string(self):
        """Test that validate_required_fields raises for empty string."""
        obj = TestableValidation(field1="value1", field2="")
        with pytest.raises(ValueError, match="cannot be empty"):
            obj.validate_required_fields("field1", "field2")

    def test_validate_required_fields_raises_for_none_value(self):
        """Test that validate_required_fields raises for None value."""
        obj = TestableValidation(field1="value1", field2=None)
        with pytest.raises(ValueError, match="cannot be empty"):
            obj.validate_required_fields("field1", "field2")

    def test_validate_field_length_passes_for_valid_length(self):
        """Test that validate_field_length passes for valid length."""
        obj = TestableValidation(field1="12345")
        assert obj.validate_field_length("field1", min_length=1, max_length=10) is True

    def test_validate_field_length_raises_for_too_short(self):
        """Test that validate_field_length raises for too short."""
        obj = TestableValidation(field1="ab")
        with pytest.raises(ValueError, match="below minimum"):
            obj.validate_field_length("field1", min_length=5, max_length=10)

    def test_validate_field_length_raises_for_too_long(self):
        """Test that validate_field_length raises for too long."""
        obj = TestableValidation(field1="abcdefghijk")
        with pytest.raises(ValueError, match="exceeds maximum"):
            obj.validate_field_length("field1", min_length=1, max_length=10)

    def test_validate_field_length_passes_for_none(self):
        """Test that validate_field_length passes for None values."""
        obj = TestableValidation(field1=None)
        assert obj.validate_field_length("field1", min_length=1, max_length=10) is True

    def test_validate_field_length_raises_for_missing_field(self):
        """Test that validate_field_length raises for missing field."""
        obj = TestableValidation()
        with pytest.raises(ValueError, match="Missing field"):
            obj.validate_field_length("missing", min_length=1, max_length=10)
