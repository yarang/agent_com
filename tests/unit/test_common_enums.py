"""
Unit tests for common enums.

Tests for centralized enums defined in common.py.
"""

import pytest

from agent_comm_core.models.common import (
    ActorType,
    AgentStatus,
    AuditAction,
    CommonStatus,
    CommunicationDirection,
    CreatorType,
    DecisionStatus,
    EntityType,
    KeyStatus,
    MeetingStatus,
    MessageType,
    ProjectStatus,
    SenderType,
)


class TestActorType:
    """Tests for ActorType enum."""

    def test_actor_type_values(self):
        """Test that ActorType has all expected values."""
        assert ActorType.USER.value == "user"
        assert ActorType.AGENT.value == "agent"
        assert ActorType.SYSTEM.value == "system"
        assert ActorType.ANONYMOUS.value == "anonymous"

    def test_actor_type_is_string_enum(self):
        """Test that ActorType is a string enum."""
        assert isinstance(ActorType.USER.value, str)

    def test_actor_type_comparison(self):
        """Test that ActorType values can be compared."""
        assert ActorType.USER == "user"
        assert ActorType.AGENT == "agent"


class TestCreatorType:
    """Tests for CreatorType alias."""

    def test_creator_type_is_actor_type(self):
        """Test that CreatorType is an alias for ActorType."""
        assert CreatorType is ActorType

    def test_creator_type_has_same_values(self):
        """Test that CreatorType has the same values as ActorType."""
        assert CreatorType.USER == ActorType.USER
        assert CreatorType.AGENT == ActorType.AGENT
        assert CreatorType.SYSTEM == ActorType.SYSTEM


class TestSenderType:
    """Tests for SenderType enum."""

    def test_sender_type_values(self):
        """Test that SenderType has all expected values."""
        assert SenderType.USER.value == "user"
        assert SenderType.AGENT.value == "agent"

    def test_sender_type_subset_of_actor_type(self):
        """Test that SenderType is a subset of ActorType."""
        assert SenderType.USER.value == ActorType.USER.value
        assert SenderType.AGENT.value == ActorType.AGENT.value


class TestCommonStatus:
    """Tests for CommonStatus enum."""

    def test_common_status_values(self):
        """Test that CommonStatus has all expected values."""
        assert CommonStatus.ACTIVE.value == "active"
        assert CommonStatus.INACTIVE.value == "inactive"
        assert CommonStatus.PENDING.value == "pending"
        assert CommonStatus.SUSPENDED.value == "suspended"
        assert CommonStatus.ARCHIVED.value == "archived"
        assert CommonStatus.DELETED.value == "deleted"
        assert CommonStatus.CANCELLED.value == "cancelled"
        assert CommonStatus.COMPLETED.value == "completed"
        assert CommonStatus.FAILED.value == "failed"
        assert CommonStatus.ERROR.value == "error"


class TestProjectStatus:
    """Tests for ProjectStatus enum."""

    def test_project_status_values(self):
        """Test that ProjectStatus has all expected values."""
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.SUSPENDED.value == "suspended"
        assert ProjectStatus.ARCHIVED.value == "archived"
        assert ProjectStatus.DELETED.value == "deleted"

    def test_project_status_subset_of_common_status(self):
        """Test that ProjectStatus values are in CommonStatus."""
        for status in ProjectStatus:
            assert status.value in CommonStatus.__members__.values()


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_agent_status_values(self):
        """Test that AgentStatus has all expected values."""
        assert AgentStatus.ONLINE.value == "online"
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.ERROR.value == "error"


class TestKeyStatus:
    """Tests for KeyStatus enum."""

    def test_key_status_values(self):
        """Test that KeyStatus has all expected values."""
        assert KeyStatus.ACTIVE.value == "active"
        assert KeyStatus.REVOKED.value == "revoked"
        assert KeyStatus.EXPIRED.value == "expired"


class TestMeetingStatus:
    """Tests for MeetingStatus enum."""

    def test_meeting_status_values(self):
        """Test that MeetingStatus has all expected values."""
        assert MeetingStatus.PENDING.value == "pending"
        assert MeetingStatus.ACTIVE.value == "active"
        assert MeetingStatus.PAUSED.value == "paused"
        assert MeetingStatus.COMPLETED.value == "completed"
        assert MeetingStatus.CANCELLED.value == "cancelled"


class TestDecisionStatus:
    """Tests for DecisionStatus enum."""

    def test_decision_status_values(self):
        """Test that DecisionStatus has all expected values."""
        assert DecisionStatus.PENDING.value == "pending"
        assert DecisionStatus.APPROVED.value == "approved"
        assert DecisionStatus.REJECTED.value == "rejected"
        assert DecisionStatus.DEFERRED.value == "deferred"


class TestCommunicationDirection:
    """Tests for CommunicationDirection enum."""

    def test_communication_direction_values(self):
        """Test that CommunicationDirection has all expected values."""
        assert CommunicationDirection.INBOUND.value == "inbound"
        assert CommunicationDirection.OUTBOUND.value == "outbound"
        assert CommunicationDirection.INTERNAL.value == "internal"


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_values(self):
        """Test that MessageType has all expected values."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.SYSTEM.value == "system"
        assert MessageType.FILE.value == "file"
        assert MessageType.EMBEDDING.value == "embedding"


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_audit_action_crud_values(self):
        """Test that AuditAction has CRUD values."""
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.READ.value == "read"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"

    def test_audit_action_auth_values(self):
        """Test that AuditAction has auth-related values."""
        assert AuditAction.AUTH_LOGIN.value == "auth_login"
        assert AuditAction.AUTH_LOGOUT.value == "auth_logout"
        assert AuditAction.AUTH_TOKEN_CREATE.value == "auth_token_create"
        assert AuditAction.AUTH_TOKEN_REFRESH.value == "auth_token_refresh"
        assert AuditAction.AUTH_TOKEN_REVOKE.value == "auth_token_revoke"

    def test_audit_action_security_values(self):
        """Test that AuditAction has security-related values."""
        assert AuditAction.PANIC.value == "panic"
        assert AuditAction.PERMISSION_DENIED.value == "permission_denied"
        assert AuditAction.SECURITY_ALERT.value == "security_alert"


class TestEntityType:
    """Tests for EntityType enum."""

    def test_entity_type_values(self):
        """Test that EntityType has all expected values."""
        assert EntityType.USER.value == "user"
        assert EntityType.PROJECT.value == "project"
        assert EntityType.AGENT_API_KEY.value == "agent_api_key"
        assert EntityType.COMMUNICATION.value == "communication"
        assert EntityType.MEETING.value == "meeting"
        assert EntityType.DECISION.value == "decision"
        assert EntityType.MESSAGE.value == "message"
        assert EntityType.SYSTEM.value == "system"


class TestEnumConsistency:
    """Tests for enum value consistency across enums."""

    def test_active_status_consistency(self):
        """Test that ACTIVE value is consistent across status enums."""
        active_value = "active"
        assert ProjectStatus.ACTIVE.value == active_value
        assert KeyStatus.ACTIVE.value == active_value
        assert MeetingStatus.ACTIVE.value == active_value
        assert CommonStatus.ACTIVE.value == active_value

    def test_pending_status_consistency(self):
        """Test that PENDING value is consistent across status enums."""
        pending_value = "pending"
        assert MeetingStatus.PENDING.value == pending_value
        assert DecisionStatus.PENDING.value == pending_value
        assert CommonStatus.PENDING.value == pending_value

    def test_deleted_status_consistency(self):
        """Test that DELETED value is consistent across status enums."""
        deleted_value = "deleted"
        assert ProjectStatus.DELETED.value == deleted_value
        assert CommonStatus.DELETED.value == deleted_value

    def test_completed_status_consistency(self):
        """Test that COMPLETED value is consistent across status enums."""
        completed_value = "completed"
        assert MeetingStatus.COMPLETED.value == completed_value
        assert CommonStatus.COMPLETED.value == completed_value

    def test_cancelled_status_consistency(self):
        """Test that CANCELLED value is consistent across status enums."""
        cancelled_value = "cancelled"
        assert MeetingStatus.CANCELLED.value == cancelled_value
        assert CommonStatus.CANCELLED.value == cancelled_value


class TestEnumIteration:
    """Tests for enum iteration and listing."""

    def test_actor_type_iteration(self):
        """Test that ActorType can be iterated."""
        statuses = list(ActorType)
        assert len(statuses) == 4
        assert ActorType.USER in statuses

    def test_project_status_iteration(self):
        """Test that ProjectStatus can be iterated."""
        statuses = list(ProjectStatus)
        assert len(statuses) == 4
        assert ProjectStatus.ACTIVE in statuses

    def test_audit_action_iteration(self):
        """Test that AuditAction can be iterated."""
        actions = list(AuditAction)
        assert len(actions) == 13
        assert AuditAction.CREATE in actions


class TestEnumStringConversion:
    """Tests for enum to/from string conversion."""

    def test_actor_type_from_string(self):
        """Test creating ActorType from string."""
        assert ActorType("user") == ActorType.USER
        assert ActorType("agent") == ActorType.AGENT

    def test_actor_type_from_invalid_string_raises(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ActorType("invalid")

    def test_status_from_string(self):
        """Test creating status enums from string."""
        assert ProjectStatus("active") == ProjectStatus.ACTIVE
        assert KeyStatus("revoked") == KeyStatus.REVOKED

    def test_enum_value_access(self):
        """Test accessing enum values."""
        assert ActorType.USER.value == "user"
        assert ProjectStatus.ACTIVE.value == "active"
