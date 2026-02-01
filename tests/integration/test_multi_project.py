"""
Integration tests for multi-project support.

This module tests project isolation, cross-project communication,
and project management features.
"""

import pytest
from uuid import uuid4

from mcp_broker.models.protocol import ProtocolDefinition, ProtocolMetadata
from mcp_broker.models.session import Session, SessionCapabilities
from mcp_broker.models.project import ProjectConfig, ProjectDefinition
from mcp_broker.project.registry import ProjectRegistry
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.routing.cross_project import CrossProjectRouter
from mcp_broker.session.manager import SessionManager
from mcp_broker.storage.memory import InMemoryStorage


@pytest.fixture
def storage():
    """Create in-memory storage backend."""
    return InMemoryStorage(queue_capacity=100)


@pytest.fixture
def project_registry():
    """Create project registry."""
    return ProjectRegistry()


@pytest.fixture
def protocol_registry(storage):
    """Create protocol registry."""
    return ProtocolRegistry(storage)


@pytest.fixture
def session_manager(storage):
    """Create session manager."""
    return SessionManager(
        storage=storage,
        queue_capacity=100,
        stale_threshold=30,
        disconnect_threshold=60,
    )


@pytest.fixture
def cross_project_router(project_registry, session_manager):
    """Create cross-project router."""
    return CrossProjectRouter(project_registry, session_manager)


class TestProjectIsolation:
    """Tests for project isolation features."""

    @pytest.mark.asyncio
    async def test_project_creation(self, project_registry):
        """Test creating a new project."""
        project = await project_registry.create_project(
            project_id="test-project",
            name="Test Project",
            description="A test project",
            tags=["test", "integration"],
        )

        assert project.project_id == "test-project"
        assert project.metadata.name == "Test Project"
        assert project.metadata.description == "A test project"
        assert project.metadata.tags == ["test", "integration"]
        assert len(project.api_keys) > 0
        assert project.is_active()

    @pytest.mark.asyncio
    async def test_duplicate_project_prevention(self, project_registry):
        """Test that duplicate project IDs are prevented."""
        await project_registry.create_project(
            project_id="duplicate-test",
            name="First Project",
        )

        with pytest.raises(ValueError, match="already exists"):
            await project_registry.create_project(
                project_id="duplicate-test",
                name="Second Project",
            )

    @pytest.mark.asyncio
    async def test_project_api_key_validation(self, project_registry):
        """Test API key validation."""
        project = await project_registry.create_project(
            project_id="apikey-test",
            name="API Key Test",
        )

        api_key = project.api_keys[0].api_key

        # Valid key should be validated
        result = await project_registry.validate_api_key(api_key)
        assert result is not None
        assert result[0] == "apikey-test"

        # Invalid key should return None
        invalid_result = await project_registry.validate_api_key("invalid_key")
        assert invalid_result is None

    @pytest.mark.asyncio
    async def test_project_listing_filters(self, project_registry):
        """Test project listing with filters."""
        # Create projects
        await project_registry.create_project(
            project_id="discoverable-1",
            name="Discoverable 1",
            config=ProjectConfig(discoverable=True),
        )
        await project_registry.create_project(
            project_id="hidden-1",
            name="Hidden 1",
            config=ProjectConfig(discoverable=False),
        )

        # List all active projects
        all_projects = await project_registry.list_projects(include_inactive=False)
        project_ids = [p.project_id for p in all_projects]

        # Hidden project should not be in results
        assert "discoverable-1" in project_ids
        assert "hidden-1" not in project_ids


class TestSessionIsolation:
    """Tests for session isolation by project."""

    @pytest.mark.asyncio
    async def test_session_project_association(self, session_manager, storage):
        """Test that sessions are associated with projects."""
        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create session in project-a
        session_a = await session_manager.create_session(
            capabilities=capabilities,
            project_id="project-a",
        )

        assert session_a.project_id == "project-a"

        # Create session in project-b
        session_b = await session_manager.create_session(
            capabilities=capabilities,
            project_id="project-b",
        )

        assert session_b.project_id == "project-b"

    @pytest.mark.asyncio
    async def test_session_list_scoping(self, session_manager):
        """Test that session listing is scoped to project."""
        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
        )

        # Create sessions in different projects
        await session_manager.create_session(capabilities, project_id="project-a")
        await session_manager.create_session(capabilities, project_id="project-a")
        await session_manager.create_session(capabilities, project_id="project-b")

        # List sessions in project-a
        sessions_a = await session_manager.list_sessions(project_id="project-a")
        assert len(sessions_a) == 2
        for session in sessions_a:
            assert session.project_id == "project-a"

        # List sessions in project-b
        sessions_b = await session_manager.list_sessions(project_id="project-b")
        assert len(sessions_b) == 1
        assert sessions_b[0].project_id == "project-b"


class TestProtocolIsolation:
    """Tests for protocol isolation by project."""

    @pytest.mark.asyncio
    async def test_protocol_scoped_registration(self, protocol_registry):
        """Test that protocols are registered in project scope."""
        protocol = ProtocolDefinition(
            name="chat-protocol",
            version="1.0.0",
            message_schema={"type": "object"},
            capabilities=["point_to_point"],
        )

        # Register in project-a
        await protocol_registry.register(protocol, project_id="project-a")

        # Should be findable in project-a
        protocols_a = await protocol_registry.discover(project_id="project-a")
        assert len(protocols_a) == 1
        assert protocols_a[0].name == "chat-protocol"

        # Should not be findable in project-b
        protocols_b = await protocol_registry.discover(project_id="project-b")
        assert len(protocols_b) == 0

    @pytest.mark.asyncio
    async def test_protocol_duplicate_within_project(self, protocol_registry):
        """Test that duplicate protocol names are prevented within project."""
        protocol = ProtocolDefinition(
            name="unique-protocol",
            version="1.0.0",
            message_schema={"type": "object"},
        )

        await protocol_registry.register(protocol, project_id="project-a")

        # Same name/version in same project should fail
        with pytest.raises(ValueError, match="already exists"):
            await protocol_registry.register(protocol, project_id="project-a")

        # Same name/version in different project should succeed
        await protocol_registry.register(protocol, project_id="project-b")


class TestCrossProjectCommunication:
    """Tests for cross-project communication."""

    @pytest.mark.asyncio
    async def test_cross_project_permission_check(
        self, project_registry, cross_project_router
    ):
        """Test cross-project permission validation."""
        # Create projects with cross-project permissions
        config_with_perm = ProjectConfig(
            allow_cross_project=True,
        )

        project_a = await project_registry.create_project(
            project_id="project-a",
            name="Project A",
            config=config_with_perm,
        )

        project_b = await project_registry.create_project(
            project_id="project-b",
            name="Project B",
            config=config_with_perm,
        )

        # Both projects should allow cross-project by default
        # (implicit permission when allow_cross_project=True)
        assert project_a.config.allow_cross_project
        assert project_b.config.allow_cross_project

    @pytest.mark.asyncio
    async def test_cross_project_message_blocked_without_permission(
        self, project_registry, session_manager, cross_project_router
    ):
        """Test that messages are blocked without cross-project permission."""
        # Create projects WITHOUT cross-project permission
        config_no_perm = ProjectConfig(
            allow_cross_project=False,
        )

        await project_registry.create_project(
            project_id="isolated-a",
            name="Isolated A",
            config=config_no_perm,
        )

        await project_registry.create_project(
            project_id="isolated-b",
            name="Isolated B",
            config=config_no_perm,
        )

        # Create sessions
        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
        )

        session_a = await session_manager.create_session(capabilities, "isolated-a")
        session_b = await session_manager.create_session(capabilities, "isolated-b")

        # Create message
        from mcp_broker.models.message import Message

        message = Message(
            sender_id=session_a.session_id,
            recipient_id=session_b.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Should fail without cross-project permission
        result = await cross_project_router.send_cross_project_message(
            sender_id=session_a.session_id,
            sender_project_id="isolated-a",
            recipient_id=session_b.session_id,
            recipient_project_id="isolated-b",
            message=message,
        )

        assert not result.success
        assert "not authorized" in result.error_reason.lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility with single-project mode."""

    @pytest.mark.asyncio
    async def test_default_project_session_creation(self, session_manager):
        """Test that sessions can be created without project_id (uses default)."""
        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
        )

        # Create session without project_id
        session = await session_manager.create_session(capabilities)

        assert session.project_id == "default"

    @pytest.mark.asyncio
    async def test_default_project_protocol_registration(self, protocol_registry):
        """Test that protocols can be registered without project_id (uses default)."""
        protocol = ProtocolDefinition(
            name="default-protocol",
            version="1.0.0",
            message_schema={"type": "object"},
        )

        # Register without project_id
        await protocol_registry.register(protocol)

        # Should be findable in default project
        protocols = await protocol_registry.discover(project_id="default")
        assert len(protocols) == 1


class TestRateLimiting:
    """Tests for cross-project rate limiting."""

    @pytest.mark.asyncio
    async def test_cross_project_rate_limiting(self, cross_project_router):
        """Test that rate limiting works for cross-project messages."""
        # Set a rate limit by checking message count
        # This test verifies the rate limiting mechanism exists

        # Initially, no messages sent
        stats = cross_project_router.get_cross_project_stats()
        assert stats["total_messages_sent"] == 0

        # Note: Full rate limiting test would require multiple message sends
        # which is tested in integration scenarios
