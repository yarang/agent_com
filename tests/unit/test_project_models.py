"""
Unit tests for project-related data models.

Tests the Pydantic models for multi-project support including
project definitions, API keys, metadata, and configuration.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from mcp_broker.models.project import (
    CrossProjectPermission,
    ProjectAPIKey,
    ProjectConfig,
    ProjectDefinition,
    ProjectInfo,
    ProjectMetadata,
    ProjectStatistics,
    ProjectStatus,
)


class TestProjectAPIKey:
    """Tests for ProjectAPIKey model."""

    def test_create_api_key_minimal(self) -> None:
        """Test creating API key with minimal fields."""
        key = ProjectAPIKey(
            key_id="default",
            api_key="myproject_default_123456789012345678901234567890",
        )

        assert key.key_id == "default"
        assert key.api_key == "myproject_default_123456789012345678901234567890"
        assert key.is_active is True
        assert key.expires_at is None

    def test_create_api_key_full(self) -> None:
        """Test creating API key with all fields."""
        now = datetime.now(UTC)
        expires = now + timedelta(days=30)

        key = ProjectAPIKey(
            key_id="admin",
            api_key="myproject_admin_123456789012345678901234567890",
            created_at=now,
            expires_at=expires,
            is_active=True,
        )

        assert key.key_id == "admin"
        assert key.created_at == now
        assert key.expires_at == expires

    def test_api_key_validation_invalid_format(self) -> None:
        """Test API key validation rejects invalid format."""
        with pytest.raises(ValidationError, match="format"):
            ProjectAPIKey(
                key_id="default",
                api_key="invalid_format",  # Missing underscores
            )

    def test_api_key_validation_too_short(self) -> None:
        """Test API key validation rejects too short keys."""
        with pytest.raises(ValidationError, match="at least 32"):
            ProjectAPIKey(
                key_id="default",
                api_key="a_b_short",  # Secret is too short
            )

    def test_api_key_format_valid(self) -> None:
        """Test valid API key format."""
        key = ProjectAPIKey(
            key_id="test",
            api_key="project_test_123456789012345678901234567890",
        )
        assert key.api_key == "project_test_123456789012345678901234567890"


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_default_config(self) -> None:
        """Test creating default configuration."""
        config = ProjectConfig()

        assert config.max_sessions == 100
        assert config.max_protocols == 50
        assert config.max_message_queue_size == 100
        assert config.allow_cross_project is False
        assert config.discoverable is True
        assert config.shared_protocols == []

    def test_custom_config(self) -> None:
        """Test creating custom configuration."""
        config = ProjectConfig(
            max_sessions=200,
            max_protocols=100,
            max_message_queue_size=200,
            allow_cross_project=True,
            discoverable=False,
            shared_protocols=["chat", "file_transfer"],
        )

        assert config.max_sessions == 200
        assert config.max_protocols == 100
        assert config.allow_cross_project is True
        assert config.discoverable is False
        assert "chat" in config.shared_protocols

    def test_config_validation_max_sessions_negative(self) -> None:
        """Test config validation rejects negative max_sessions."""
        with pytest.raises(ValidationError):
            ProjectConfig(max_sessions=-1)

    def test_config_validation_max_sessions_zero(self) -> None:
        """Test config validation rejects zero max_sessions."""
        with pytest.raises(ValidationError):
            ProjectConfig(max_sessions=0)


class TestProjectMetadata:
    """Tests for ProjectMetadata model."""

    def test_minimal_metadata(self) -> None:
        """Test creating minimal metadata."""
        metadata = ProjectMetadata(name="My Project")

        assert metadata.name == "My Project"
        assert metadata.description == ""
        assert metadata.tags == []
        assert metadata.owner is None

    def test_full_metadata(self) -> None:
        """Test creating full metadata."""
        metadata = ProjectMetadata(
            name="My Project",
            description="A test project",
            tags=["test", "demo"],
            owner="user123",
        )

        assert metadata.name == "My Project"
        assert metadata.description == "A test project"
        assert "test" in metadata.tags
        assert metadata.owner == "user123"

    def test_metadata_name_too_long(self) -> None:
        """Test metadata validation rejects name > 100 characters."""
        long_name = "a" * 101
        with pytest.raises(ValidationError, match="max_length"):
            ProjectMetadata(name=long_name)

    def test_metadata_description_too_long(self) -> None:
        """Test metadata validation rejects description > 500 characters."""
        long_desc = "a" * 501
        with pytest.raises(ValidationError, match="max_length"):
            ProjectMetadata(name="Test", description=long_desc)


class TestProjectStatistics:
    """Tests for ProjectStatistics model."""

    def test_default_statistics(self) -> None:
        """Test creating default statistics."""
        stats = ProjectStatistics()

        assert stats.session_count == 0
        assert stats.message_count == 0
        assert stats.protocol_count == 0
        assert isinstance(stats.last_activity, datetime)

    def test_custom_statistics(self) -> None:
        """Test creating custom statistics."""
        now = datetime.now(UTC)
        stats = ProjectStatistics(
            session_count=10,
            message_count=1000,
            protocol_count=5,
            last_activity=now,
        )

        assert stats.session_count == 10
        assert stats.message_count == 1000
        assert stats.protocol_count == 5
        assert stats.last_activity == now

    def test_statistics_validation_negative_count(self) -> None:
        """Test statistics validation rejects negative counts."""
        with pytest.raises(ValidationError):
            ProjectStatistics(session_count=-1)


class TestProjectStatus:
    """Tests for ProjectStatus model."""

    def test_default_status(self) -> None:
        """Test creating default status."""
        status = ProjectStatus()

        assert status.status == "active"
        assert isinstance(status.created_at, datetime)
        assert isinstance(status.last_modified, datetime)

    def test_custom_status(self) -> None:
        """Test creating custom status."""
        now = datetime.now(UTC)
        status = ProjectStatus(
            status="inactive",
            created_at=now,
            last_modified=now,
        )

        assert status.status == "inactive"

    def test_status_invalid_value(self) -> None:
        """Test status validation rejects invalid values."""
        with pytest.raises(ValidationError):
            ProjectStatus(status="invalid_status")


class TestCrossProjectPermission:
    """Tests for CrossProjectPermission model."""

    def test_minimal_permission(self) -> None:
        """Test creating minimal permission."""
        perm = CrossProjectPermission(target_project_id="other_project")

        assert perm.target_project_id == "other_project"
        assert perm.allowed_protocols == []
        assert perm.message_rate_limit == 0

    def test_full_permission(self) -> None:
        """Test creating full permission."""
        perm = CrossProjectPermission(
            target_project_id="other_project",
            allowed_protocols=["chat", "file_transfer"],
            message_rate_limit=100,
        )

        assert perm.target_project_id == "other_project"
        assert "chat" in perm.allowed_protocols
        assert perm.message_rate_limit == 100

    def test_permission_validation_invalid_project_id(self) -> None:
        """Test permission validation rejects invalid project_id."""
        with pytest.raises(ValidationError, match="pattern"):
            CrossProjectPermission(target_project_id="Invalid-ID")

    def test_permission_validation_negative_rate_limit(self) -> None:
        """Test permission validation rejects negative rate limit."""
        with pytest.raises(ValidationError):
            CrossProjectPermission(
                target_project_id="other",
                message_rate_limit=-1,
            )


class TestProjectDefinition:
    """Tests for ProjectDefinition model."""

    def test_minimal_project(self) -> None:
        """Test creating minimal project definition."""
        project = ProjectDefinition(
            project_id="test_project",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project_default_abc123def456",
                )
            ],
        )

        assert project.project_id == "test_project"
        assert len(project.api_keys) == 1
        assert project.is_active()

    def test_full_project(self) -> None:
        """Test creating full project definition."""
        project = ProjectDefinition(
            project_id="test_project",
            metadata=ProjectMetadata(
                name="Test Project",
                description="A test project",
            ),
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project_default_abc123def456",
                )
            ],
            config=ProjectConfig(max_sessions=200),
            cross_project_permissions=[
                CrossProjectPermission(target_project_id="other")
            ],
        )

        assert project.project_id == "test_project"
        assert project.metadata.name == "Test Project"
        assert project.config.max_sessions == 200
        assert len(project.cross_project_permissions) == 1

    def test_project_validation_reserved_id(self) -> None:
        """Test project validation rejects reserved IDs."""
        with pytest.raises(ValidationError, match="reserved"):
            ProjectDefinition(
                project_id="system",  # "system" is reserved
                api_keys=[
                    ProjectAPIKey(
                        key_id="default",
                        api_key="system_default_123456789012345678901234567890",
                    )
                ],
            )

    def test_project_validation_no_api_keys(self) -> None:
        """Test project validation requires at least one API key."""
        with pytest.raises(ValidationError, match="at least one API key"):
            ProjectDefinition(project_id="test_project", api_keys=[])

    def test_project_is_active(self) -> None:
        """Test project is_active method."""
        active_project = ProjectDefinition(
            project_id="active_project",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="active_project_default_abc123def456",
                )
            ],
            status=ProjectStatus(status="active"),
        )
        assert active_project.is_active()

        inactive_project = ProjectDefinition(
            project_id="inactive_project",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="inactive_project_default_abc123def456",
                )
            ],
            status=ProjectStatus(status="inactive"),
        )
        assert not inactive_project.is_active()

    def test_project_has_active_api_key(self) -> None:
        """Test project has_active_api_key method."""
        project = ProjectDefinition(
            project_id="test_project",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project_default_abc123def456",
                    is_active=True,
                )
            ],
        )
        assert project.has_active_api_key()

        # Test with inactive key
        project_inactive = ProjectDefinition(
            project_id="test_project2",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project2_default_abc123def456",
                    is_active=False,
                )
            ],
        )
        assert not project_inactive.has_active_api_key()

    def test_project_get_active_api_keys(self) -> None:
        """Test project get_active_api_keys method."""
        project = ProjectDefinition(
            project_id="test_project",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project_default_abc123def456",
                    is_active=True,
                ),
                ProjectAPIKey(
                    key_id="admin",
                    api_key="test_project_admin_xyz789",
                    is_active=False,
                ),
            ],
        )

        active_keys = project.get_active_api_keys()
        assert len(active_keys) == 1
        assert active_keys[0].key_id == "default"


class TestProjectInfo:
    """Tests for ProjectInfo model."""

    def test_from_definition(self) -> None:
        """Test creating ProjectInfo from ProjectDefinition."""
        project = ProjectDefinition(
            project_id="test_project",
            metadata=ProjectMetadata(
                name="Test Project",
                description="A test project",
            ),
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project_default_abc123def456",
                )
            ],
            config=ProjectConfig(allow_cross_project=True),
        )

        info = ProjectInfo.from_definition(project)

        assert info.project_id == "test_project"
        assert info.metadata.name == "Test Project"
        assert info.config_subset["allow_cross_project"] is True
        assert info.status == "active"
        # API keys should not be in public info
        assert "api_keys" not in info.config_subset

    def test_from_definition_minimal(self) -> None:
        """Test ProjectInfo from minimal ProjectDefinition."""
        project = ProjectDefinition(
            project_id="test_project",
            api_keys=[
                ProjectAPIKey(
                    key_id="default",
                    api_key="test_project_default_abc123def456",
                )
            ],
        )

        info = ProjectInfo.from_definition(project)

        assert info.project_id == "test_project"
        assert isinstance(info.metadata, ProjectMetadata)
        assert isinstance(info.statistics, ProjectStatistics)
        assert info.status == "active"
