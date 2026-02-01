"""
Unit tests for session-related Pydantic models.

Tests the Session, SessionCapabilities, and SessionStatus
models for validation and business logic methods.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pytest_mock import MockerFixture
from uuid import UUID, uuid4

from mcp_broker.models.session import (
    Session,
    SessionCapabilities,
    SessionStatus,
)
from tests.conftest import (
    active_session,
    disconnected_session,
    session_a,
    session_b,
    session_capabilities,
    session_capabilities_limited,
    stale_session,
)


class TestSessionCapabilities:
    """Tests for SessionCapabilities model."""

    def test_create_minimal_capabilities(self) -> None:
        """Test creating capabilities with no protocols."""
        caps = SessionCapabilities()
        assert caps.supported_protocols == {}
        assert caps.supported_features == []

    def test_create_full_capabilities(self, session_capabilities: SessionCapabilities) -> None:
        """Test creating capabilities with all fields."""
        assert "chat_message" in session_capabilities.supported_protocols
        assert "1.0.0" in session_capabilities.supported_protocols["chat_message"]
        assert "point_to_point" in session_capabilities.supported_features

    def test_features_deduplication(self) -> None:
        """Test duplicate features are removed."""
        caps = SessionCapabilities(
            supported_features=["point_to_point", "point_to_point", "broadcast"]
        )
        assert len(caps.supported_features) == 2

    def test_protocols_with_multiple_versions(self) -> None:
        """Test protocol with multiple supported versions."""
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0", "1.1.0", "2.0.0"]}
        )
        assert len(caps.supported_protocols["chat"]) == 3


class TestSession:
    """Tests for Session model."""

    def test_create_session_minimal(self) -> None:
        """Test creating session with minimal fields."""
        session = Session()
        assert isinstance(session.session_id, UUID)
        assert isinstance(session.connection_time, datetime)
        assert isinstance(session.last_heartbeat, datetime)
        assert session.status == "active"
        assert session.queue_size == 0

    def test_create_session_full(self, active_session: Session) -> None:
        """Test creating session with all fields."""
        assert active_session.session_id is not None
        assert active_session.status == "active"
        assert active_session.capabilities is not None

    def test_heartbeat_not_in_future(self) -> None:
        """Test heartbeat cannot be in the future."""
        future_time = datetime.now(UTC) + timedelta(seconds=10)
        with pytest.raises(ValueError, match="future"):
            Session(
                last_heartbeat=future_time,
            )

    def test_queue_size_non_negative(self) -> None:
        """Test queue size cannot be negative."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            Session(queue_size=-1)

    def test_is_stale_true(self, stale_session: Session) -> None:
        """Test is_stale returns True for stale session."""
        assert stale_session.is_stale(stale_threshold_seconds=30) is True

    def test_is_stale_false(self, active_session: Session) -> None:
        """Test is_stale returns False for active session."""
        assert active_session.is_stale(stale_threshold_seconds=30) is False

    def test_should_disconnect_true(self) -> None:
        """Test should_disconnect for very old session."""
        old_time = datetime.now(UTC) - timedelta(seconds=70)
        session = Session(
            session_id=uuid4(),
            last_heartbeat=old_time,
        )
        assert session.should_disconnect(disconnect_threshold_seconds=60) is True

    def test_should_disconnect_false(self, active_session: Session) -> None:
        """Test should_disconnect for active session."""
        assert active_session.should_disconnect(disconnect_threshold_seconds=60) is False

    def test_supports_protocol_true(self, session_a: Session) -> None:
        """Test supports_protocol returns True when supported."""
        assert session_a.supports_protocol("chat_message", "1.0.0") is True
        assert session_a.supports_protocol("chat_message", "1.1.0") is True

    def test_supports_protocol_false_wrong_version(self, session_a: Session) -> None:
        """Test supports_protocol returns False for unsupported version."""
        assert session_a.supports_protocol("chat_message", "2.0.0") is False

    def test_supports_protocol_false_wrong_protocol(self, session_a: Session) -> None:
        """Test supports_protocol returns False for unknown protocol."""
        assert session_a.supports_protocol("unknown_protocol", "1.0.0") is False

    def test_find_common_protocols(self, session_a: Session, session_b: Session) -> None:
        """Test find_common_protocols returns intersection."""
        common = session_a.find_common_protocols(session_b)
        assert "chat_message" in common
        assert common["chat_message"] == "1.0.0"
        assert "file_transfer" not in common  # session_b doesn't support it

    def test_find_common_protocols_empty(self) -> None:
        """Test find_common_protocols with no overlap."""
        session1 = Session(
            capabilities=SessionCapabilities(
                supported_protocols={"chat": ["1.0.0"]}
            )
        )
        session2 = Session(
            capabilities=SessionCapabilities(
                supported_protocols={"file": ["1.0.0"]}
            )
        )
        common = session1.find_common_protocols(session2)
        assert common == {}

    def test_status_values(self) -> None:
        """Test valid session status values."""
        valid_statuses: list[SessionStatus] = ["active", "stale", "disconnected"]
        for status in valid_statuses:
            session = Session(status=status)
            assert session.status == status
