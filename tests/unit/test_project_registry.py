"""
Unit tests for project registry.

Tests the ProjectRegistry class which manages projects,
API keys, and project-scoped storage namespace.
"""

import pytest

from mcp_broker.models.project import (
    ProjectAPIKey,
    ProjectConfig,
    ProjectDefinition,
    ProjectInfo,
)
from mcp_broker.project.registry import ProjectRegistry


class TestProjectRegistry:
    """Tests for ProjectRegistry class."""

    async def test_create_project_minimal(self) -> None:
        """Test creating a project with minimal parameters."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test Project",
        )

        assert project.project_id == "test_project"
        assert project.metadata.name == "Test Project"
        assert len(project.api_keys) == 1
        assert project.api_keys[0].is_active
        assert project.config.max_sessions == 100  # default

    async def test_create_project_full(self) -> None:
        """Test creating a project with all parameters."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test Project",
            description="A test project",
            config=ProjectConfig(max_sessions=200),
            tags=["test", "demo"],
            owner="user123",
        )

        assert project.project_id == "test_project"
        assert project.metadata.name == "Test Project"
        assert project.metadata.description == "A test project"
        assert project.config.max_sessions == 200
        assert "test" in project.metadata.tags
        assert project.metadata.owner == "user123"

    async def test_create_project_duplicate(self) -> None:
        """Test creating duplicate project raises error."""
        registry = ProjectRegistry()

        await registry.create_project(
            project_id="test_project",
            name="Test Project",
        )

        with pytest.raises(ValueError, match="already exists"):
            await registry.create_project(
                project_id="test_project",
                name="Another Name",
            )

    async def test_get_project_exists(self) -> None:
        """Test getting an existing project."""
        registry = ProjectRegistry()

        created = await registry.create_project(
            project_id="test_project",
            name="Test Project",
        )

        retrieved = await registry.get_project("test_project")

        assert retrieved is not None
        assert retrieved.project_id == "test_project"
        assert retrieved.metadata.name == "Test Project"

    async def test_get_project_not_exists(self) -> None:
        """Test getting a non-existent project."""
        registry = ProjectRegistry()

        retrieved = await registry.get_project("nonexistent")

        assert retrieved is None

    async def test_list_projects_all(self) -> None:
        """Test listing all projects."""
        registry = ProjectRegistry()

        await registry.create_project(project_id="project1", name="Project 1")
        await registry.create_project(project_id="project2", name="Project 2")
        await registry.create_project(project_id="project3", name="Project 3")

        projects = await registry.list_projects()

        assert len(projects) == 3
        project_ids = {p.project_id for p in projects}
        assert project_ids == {"project1", "project2", "project3"}

    async def test_list_projects_with_name_filter(self) -> None:
        """Test listing projects with name filter."""
        registry = ProjectRegistry()

        await registry.create_project(project_id="project1", name="Alpha Project")
        await registry.create_project(project_id="project2", name="Beta Project")
        await registry.create_project(project_id="project3", name="Gamma Project")

        projects = await registry.list_projects(name_filter="project")

        assert len(projects) == 3

        projects = await registry.list_projects(name_filter="alpha")

        assert len(projects) == 1
        assert projects[0].project_id == "project1"

    async def test_list_projects_exclude_inactive(self) -> None:
        """Test listing projects excludes inactive by default."""
        registry = ProjectRegistry()

        await registry.create_project(project_id="project1", name="Active")
        await registry.create_project(project_id="project2", name="Inactive")

        # Deactivate project2
        project2 = await registry.get_project("project2")
        assert project2 is not None
        project2.status.status = "inactive"

        # List without inactive
        active_only = await registry.list_projects(include_inactive=False)
        assert len(active_only) == 1
        assert active_only[0].project_id == "project1"

        # List with inactive
        all_projects = await registry.list_projects(include_inactive=True)
        assert len(all_projects) == 2

    async def test_update_project(self) -> None:
        """Test updating a project."""
        registry = ProjectRegistry()

        await registry.create_project(
            project_id="test_project",
            name="Original Name",
        )

        updated = await registry.update_project(
            project_id="test_project",
            name="Updated Name",
            description="Updated description",
        )

        assert updated.metadata.name == "Updated Name"
        assert updated.metadata.description == "Updated description"

    async def test_update_project_not_exists(self) -> None:
        """Test updating non-existent project raises error."""
        registry = ProjectRegistry()

        with pytest.raises(ValueError, match="not found"):
            await registry.update_project(
                project_id="nonexistent",
                name="New Name",
            )

    async def test_delete_project_success(self) -> None:
        """Test deleting a project."""
        registry = ProjectRegistry()

        await registry.create_project(project_id="test_project", name="Test")

        result = await registry.delete_project("test_project")

        assert result is True
        retrieved = await registry.get_project("test_project")
        assert retrieved is None

    async def test_delete_project_not_exists(self) -> None:
        """Test deleting non-existent project returns False."""
        registry = ProjectRegistry()

        result = await registry.delete_project("nonexistent")

        assert result is False

    async def test_delete_project_with_active_sessions(self) -> None:
        """Test deleting project with active sessions raises error."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test",
        )

        # Simulate active sessions
        project.statistics.session_count = 5

        with pytest.raises(ValueError, match="active sessions"):
            await registry.delete_project("test_project")

    async def test_validate_api_key_valid(self) -> None:
        """Test validating a valid API key."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test",
        )

        api_key = project.api_keys[0].api_key

        result = await registry.validate_api_key(api_key)

        assert result is not None
        project_id, key_id = result
        assert project_id == "test_project"

    async def test_validate_api_key_invalid_format(self) -> None:
        """Test validating API key with invalid format."""
        registry = ProjectRegistry()

        result = await registry.validate_api_key("invalid_key")

        assert result is None

    async def test_validate_api_key_unknown_project(self) -> None:
        """Test validating API key for unknown project."""
        registry = ProjectRegistry()

        result = await registry.validate_api_key("unknown_default_abc123")

        assert result is None

    async def test_validate_api_key_inactive(self) -> None:
        """Test validating inactive API key."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test",
        )

        # Deactivate the key
        project.api_keys[0].is_active = False
        api_key = project.api_keys[0].api_key

        result = await registry.validate_api_key(api_key)

        assert result is None

    async def test_rotate_api_keys_all(self) -> None:
        """Test rotating all API keys."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test",
        )

        old_key = project.api_keys[0].api_key

        new_keys = await registry.rotate_api_keys(
            project_id="test_project",
            grace_period_seconds=0,
        )

        assert len(new_keys) == 1
        assert new_keys[0].api_key != old_key

        # Old key should be expired immediately
        result = await registry.validate_api_key(old_key)
        assert result is None

    async def test_rotate_api_keys_specific(self) -> None:
        """Test rotating specific API key."""
        registry = ProjectRegistry()

        project = await registry.create_project(
            project_id="test_project",
            name="Test",
        )

        # Add another key
        from mcp_broker.models.project import ProjectAPIKey
        project.api_keys.append(
            ProjectAPIKey(
                key_id="admin",
                api_key="test_project_admin_secret",
            )
        )

        old_default_key = project.api_keys[0].api_key
        old_admin_key = project.api_keys[1].api_key

        # Rotate only default key
        new_keys = await registry.rotate_api_keys(
            project_id="test_project",
            key_id="default",
            grace_period_seconds=0,
        )

        assert len(new_keys) == 1
        assert new_keys[0].key_id != "default"

        # Default key should be expired
        result = await registry.validate_api_key(old_default_key)
        assert result is None

        # Admin key should still work
        result = await registry.validate_api_key(old_admin_key)
        assert result is not None

    async def test_rotate_api_keys_not_exists(self) -> None:
        """Test rotating keys for non-existent project."""
        registry = ProjectRegistry()

        with pytest.raises(ValueError, match="not found"):
            await registry.rotate_api_keys(
                project_id="nonexistent",
            )

    async def test_update_statistics(self) -> None:
        """Test updating project statistics."""
        registry = ProjectRegistry()

        await registry.create_project(
            project_id="test_project",
            name="Test",
        )

        await registry.update_statistics(
            project_id="test_project",
            session_count_delta=5,
            message_count_delta=100,
            protocol_count_delta=2,
        )

        project = await registry.get_project("test_project")
        assert project is not None
        assert project.statistics.session_count == 5
        assert project.statistics.message_count == 100
        assert project.statistics.protocol_count == 2

    async def test_ensure_default_project(self) -> None:
        """Test ensuring default project exists."""
        registry = ProjectRegistry()

        # Call ensure
        registry._ensure_default_project()

        project = await registry.get_project("default")

        assert project is not None
        assert project.metadata.name == "Default Project"
        assert len(project.api_keys) == 1
        assert project.api_keys[0].key_id == "default"

    async def test_ensure_default_project_idempotent(self) -> None:
        """Test ensure_default_project is idempotent."""
        registry = ProjectRegistry()

        # Call twice
        registry._ensure_default_project()
        registry._ensure_default_project()

        # Should only have one default project
        project = await registry.get_project("default")
        assert project is not None
        assert len(project.api_keys) == 1
