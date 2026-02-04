"""
Unit tests for Admin Permission System.

Tests for admin role detection, cross-project access control,
and permission caching.
"""

import pytest

from mcp_broker.core.admin import AdminPermissionManager
from mcp_broker.models.project import (
    CrossProjectPermission,
    ProjectAPIKey,
    ProjectConfig,
)


class TestAdminRoleDetection:
    """Tests for admin role detection from API keys."""

    def test_is_admin_key_with_admin_prefix(self) -> None:
        """Test detection of admin key."""
        # Create a manager with mock registry
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Admin key format (at least 32 chars for secret part)
        admin_key = "myproject_admin_abcdefghijklmnopqrstuvwxyz123456"

        assert manager.is_admin_key(admin_key, "myproject") is True

    def test_is_admin_key_with_owner_prefix(self) -> None:
        """Test detection of owner key."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Owner key format
        owner_key = "myproject_owner_abcdefghijklmnopqrstuvwxyz123456"

        assert manager.is_admin_key(owner_key, "myproject") is True

    def test_is_admin_key_with_regular_key(self) -> None:
        """Test regular key is not admin."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Regular key format
        regular_key = "myproject_key1_abcdefghijklmnopqrstuvwxyz123456"

        assert manager.is_admin_key(regular_key, "myproject") is False

    def test_is_admin_key_with_malformed_key(self) -> None:
        """Test malformed key returns False."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Malformed key
        malformed_key = "invalid_key"

        assert manager.is_admin_key(malformed_key, "any_project") is False


class TestCrossProjectAccess:
    """Tests for cross-project access control."""

    @pytest.mark.asyncio
    async def test_same_project_access_allowed(self) -> None:
        """Test same project access is always allowed."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects
        await registry.create_project("project_a", "Project A")

        # Same project access
        result = await manager.can_access_project("project_a", "project_a")

        assert result is True

    @pytest.mark.asyncio
    async def test_admin_key_cross_project_access(self) -> None:
        """Test admin key allows cross-project access."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects with cross-project disabled
        config = ProjectConfig(allow_cross_project=False)
        await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # Admin key bypasses restriction
        admin_key = "project_a_admin_abcdefghijklmnopqrstuvwxyz123456"

        result = await manager.can_access_project("project_a", "project_b", admin_key)

        assert result is True

    @pytest.mark.asyncio
    async def test_cross_project_access_with_permission(self) -> None:
        """Test cross-project access with explicit permission."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects with cross-project enabled
        config = ProjectConfig(allow_cross_project=True)
        project_a = await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # Add cross-project permission
        permission = CrossProjectPermission(
            target_project_id="project_b", allowed_protocols=[], message_rate_limit=0
        )
        project_a.cross_project_permissions.append(permission)

        # Access should be allowed
        result = await manager.can_access_project("project_a", "project_b")

        assert result is True

    @pytest.mark.asyncio
    async def test_cross_project_access_without_permission(self) -> None:
        """Test cross-project access denied without permission."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects with cross-project disabled
        config = ProjectConfig(allow_cross_project=False)
        await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # Access should be denied
        result = await manager.can_access_project("project_a", "project_b")

        assert result is False

    @pytest.mark.asyncio
    async def test_cross_project_to_nonexistent_project(self) -> None:
        """Test cross-project access to non-existent project."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create only project_a
        await registry.create_project("project_a", "Project A")

        # Access to non-existent project
        result = await manager.can_access_project("project_a", "project_nonexistent")

        assert result is False


class TestCrossProjectMessaging:
    """Tests for cross-project message sending permissions."""

    @pytest.mark.asyncio
    async def test_send_message_to_same_project(self) -> None:
        """Test messaging within same project is allowed."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        await registry.create_project("project_a", "Project A")

        # Same project messaging
        result = await manager.can_send_cross_project_message("project_a", "project_a", "chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_admin_send_cross_project_message(self) -> None:
        """Test admin can send cross-project messages."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects with cross-project disabled
        config = ProjectConfig(allow_cross_project=False)
        await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # Admin key bypasses restrictions
        admin_key = "project_a_admin_abcdefghijklmnopqrstuvwxyz123456"

        result = await manager.can_send_cross_project_message(
            "project_a", "project_b", "chat", admin_key
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_message_with_protocol_whitelist(self) -> None:
        """Test protocol whitelist enforcement."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects with cross-project enabled
        config = ProjectConfig(allow_cross_project=True)
        project_a = await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # Add permission with protocol whitelist
        permission = CrossProjectPermission(
            target_project_id="project_b",
            allowed_protocols=["chat"],
            message_rate_limit=0,
        )
        project_a.cross_project_permissions.append(permission)

        # Allowed protocol
        result1 = await manager.can_send_cross_project_message("project_a", "project_b", "chat")
        assert result1 is True

        # Blocked protocol
        result2 = await manager.can_send_cross_project_message(
            "project_a", "project_b", "file_transfer"
        )
        assert result2 is False


class TestRateLimits:
    """Tests for message rate limiting."""

    @pytest.mark.asyncio
    async def test_admin_key_unlimited_rate(self) -> None:
        """Test admin keys have unlimited rate."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        await registry.create_project("project_a", "Project A")
        await registry.create_project("project_b", "Project B")

        admin_key = "project_a_admin_abcdefghijklmnopqrstuvwxyz123456"

        limit = await manager.get_message_rate_limit("project_a", "project_b", admin_key)

        assert limit == 0  # 0 means unlimited

    @pytest.mark.asyncio
    async def test_explicit_rate_limit(self) -> None:
        """Test explicit rate limit from permission."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects
        config = ProjectConfig(allow_cross_project=True)
        project_a = await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # Add permission with rate limit
        permission = CrossProjectPermission(
            target_project_id="project_b",
            allowed_protocols=[],
            message_rate_limit=100,  # 100 messages per minute
        )
        project_a.cross_project_permissions.append(permission)

        limit = await manager.get_message_rate_limit("project_a", "project_b")

        assert limit == 100


class TestProjectManagement:
    """Tests for project management permissions."""

    @pytest.mark.asyncio
    async def test_admin_can_manage_project(self) -> None:
        """Test admin key can manage project."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create project with admin key (32+ characters)
        api_key = ProjectAPIKey(
            key_id="admin",
            api_key="myproject_admin_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project = await registry.create_project("myproject", "My Project")
        project.api_keys.append(api_key)

        result = await manager.can_manage_project("myproject", api_key.api_key, "update")

        assert result is True

    @pytest.mark.asyncio
    async def test_regular_key_cannot_manage_project(self) -> None:
        """Test regular key cannot manage project."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create project with regular key (32+ characters)
        api_key = ProjectAPIKey(
            key_id="regular",
            api_key="myproject_regular_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project = await registry.create_project("myproject", "My Project")
        project.api_keys.append(api_key)

        result = await manager.can_manage_project("myproject", api_key.api_key, "update")

        assert result is False

    @pytest.mark.asyncio
    async def test_wrong_project_key_cannot_manage(self) -> None:
        """Test key from wrong project cannot manage."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create two projects
        api_key_a = ProjectAPIKey(
            key_id="admin",
            api_key="projecta_admin_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project_a = await registry.create_project("project_a", "Project A")
        project_a.api_keys.append(api_key_a)

        await registry.create_project("project_b", "Project B")

        # Project A admin key cannot manage Project B
        result = await manager.can_manage_project("project_b", api_key_a.api_key, "update")

        assert result is False


class TestPermissionCaching:
    """Tests for permission caching functionality."""

    @pytest.mark.asyncio
    async def test_permission_cache_hit(self) -> None:
        """Test cached permissions are returned."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry, cache_ttl_seconds=60)

        # Create projects
        config = ProjectConfig(allow_cross_project=False)
        await registry.create_project("project_a", "Project A", config=config)
        await registry.create_project("project_b", "Project B", config=config)

        # First call - caches the result
        result1 = await manager.can_access_project("project_a", "project_b")

        # Second call - should return cached result
        result2 = await manager.can_access_project("project_a", "project_b")

        assert result1 == result2
        assert result1 is False

    def test_clear_permission_cache(self) -> None:
        """Test clearing permission cache."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Add something to cache
        cache_key = ("project_a", "access_project", "project_b")
        manager._cache_permission(cache_key, True)

        # Verify cache has content
        assert len(manager._permission_cache) > 0

        # Clear cache
        manager.clear_permission_cache()

        # Verify cache is empty
        assert len(manager._permission_cache) == 0


class TestCrossProjectConfigValidation:
    """Tests for cross-project configuration validation."""

    @pytest.mark.asyncio
    async def test_validate_cross_project_config_success(self) -> None:
        """Test valid cross-project configuration."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects
        api_key = ProjectAPIKey(
            key_id="admin",
            api_key="project_a_admin_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project_a = await registry.create_project("project_a", "Project A")
        project_a.api_keys.append(api_key)
        await registry.create_project("project_b", "Project B")

        # Valid configuration
        is_valid, error = await manager.validate_cross_project_config(
            "project_a",
            "project_b",
            allowed_protocols=["chat"],
            rate_limit=100,
            api_key=api_key.api_key,
        )

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_cross_project_config_non_admin(self) -> None:
        """Test validation fails for non-admin key."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects
        await registry.create_project("project_a", "Project A")
        await registry.create_project("project_b", "Project B")

        regular_key = "project_a_regular_abcdefghijklmnopqrstuvwxyz123456"

        # Non-admin key should fail
        is_valid, error = await manager.validate_cross_project_config(
            "project_a",
            "project_b",
            allowed_protocols=["chat"],
            rate_limit=100,
            api_key=regular_key,
        )

        assert is_valid is False
        assert "Admin permission required" in error

    @pytest.mark.asyncio
    async def test_validate_cross_project_config_same_project(self) -> None:
        """Test validation fails for same project."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create project with admin key
        api_key = ProjectAPIKey(
            key_id="admin",
            api_key="project_a_admin_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project_a = await registry.create_project("project_a", "Project A")
        project_a.api_keys.append(api_key)

        # Same project should fail
        is_valid, error = await manager.validate_cross_project_config(
            "project_a",
            "project_a",  # Same project
            allowed_protocols=["chat"],
            rate_limit=100,
            api_key=api_key.api_key,
        )

        assert is_valid is False
        assert "self" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_cross_project_config_target_not_found(self) -> None:
        """Test validation fails for non-existent target."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create only project_a
        api_key = ProjectAPIKey(
            key_id="admin",
            api_key="project_a_admin_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project_a = await registry.create_project("project_a", "Project A")
        project_a.api_keys.append(api_key)

        # Non-existent target should fail
        is_valid, error = await manager.validate_cross_project_config(
            "project_a",
            "project_nonexistent",  # Doesn't exist
            allowed_protocols=["chat"],
            rate_limit=100,
            api_key=api_key.api_key,
        )

        assert is_valid is False
        assert "not found" in error

    @pytest.mark.asyncio
    async def test_validate_cross_project_config_negative_rate_limit(self) -> None:
        """Test validation fails for negative rate limit."""
        from mcp_broker.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        manager = AdminPermissionManager(registry)

        # Create projects
        api_key = ProjectAPIKey(
            key_id="admin",
            api_key="project_a_admin_abcdefghijklmnopqrstuvwxyz123456",
            is_active=True,
        )
        project_a = await registry.create_project("project_a", "Project A")
        project_a.api_keys.append(api_key)
        await registry.create_project("project_b", "Project B")

        # Negative rate limit should fail
        is_valid, error = await manager.validate_cross_project_config(
            "project_a",
            "project_b",
            allowed_protocols=["chat"],
            rate_limit=-1,  # Invalid
            api_key=api_key.api_key,
        )

        assert is_valid is False
        assert "rate limit" in error.lower()
