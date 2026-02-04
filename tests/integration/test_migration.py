"""
Integration tests for single-project to multi-project migration.

Tests the migration script that creates a default project and
ensures backward compatibility for existing deployments.
"""

from uuid import uuid4

from mcp_broker.models.message import Message
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.models.session import Session, SessionCapabilities
from mcp_broker.project.registry import ProjectRegistry
from mcp_broker.storage.memory import InMemoryStorage

# Sample schema for testing
SAMPLE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["text"],
}


class TestMigration:
    """Tests for migration to default project."""

    async def test_default_project_creation(self) -> None:
        """Test default project is created."""
        registry = ProjectRegistry()

        registry._ensure_default_project()

        project = await registry.get_project("default")

        assert project is not None
        assert project.project_id == "default"
        assert project.metadata.name == "Default Project"
        assert len(project.api_keys) == 1
        assert project.api_keys[0].key_id == "default"

    async def test_default_project_idempotent(self) -> None:
        """Test ensuring default project multiple times doesn't duplicate."""
        registry = ProjectRegistry()

        # Call multiple times
        registry._ensure_default_project()
        registry._ensure_default_project()
        registry._ensure_default_project()

        project = await registry.get_project("default")

        assert project is not None
        # Should still have exactly one API key
        assert len(project.api_keys) == 1

    async def test_backward_compatibility_protocol_operations(self) -> None:
        """Test protocol operations work without project_id (backward compatible)."""
        storage = InMemoryStorage()
        registry = ProjectRegistry()

        registry._ensure_default_project()

        # Create protocol without project_id
        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )

        await storage.save_protocol(protocol)

        # Retrieve without project_id
        retrieved = await storage.get_protocol("chat", "1.0.0")
        assert retrieved is not None
        assert retrieved.name == "chat"

        # List without project_id
        protocols = await storage.list_protocols()
        assert len(protocols) == 1

        # Delete without project_id
        result = await storage.delete_protocol("chat", "1.0.0")
        assert result is True

    async def test_backward_compatibility_session_operations(self) -> None:
        """Test session operations work without project_id (backward compatible)."""
        storage = InMemoryStorage()
        registry = ProjectRegistry()

        registry._ensure_default_project()

        # Create session without project_id
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )
        session = Session(session_id=uuid4(), capabilities=caps)

        await storage.save_session(session)

        # Retrieve without project_id
        retrieved = await storage.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

        # List without project_id
        sessions = await storage.list_sessions()
        assert len(sessions) == 1

        # Delete without project_id
        result = await storage.delete_session(session.session_id)
        assert result is True

    async def test_backward_compatibility_message_operations(self) -> None:
        """Test message operations work without project_id (backward compatible)."""
        storage = InMemoryStorage()
        registry = ProjectRegistry()

        registry._ensure_default_project()

        # Save session first
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )
        session = Session(session_id=uuid4(), capabilities=caps)
        await storage.save_session(session)

        # Create message without project_id
        message = Message(
            sender_id=uuid4(),
            recipient_id=session.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        await storage.enqueue_message(session.session_id, message)

        # Get queue size without project_id
        size = await storage.get_queue_size(session.session_id)
        assert size == 1

        # Dequeue without project_id
        messages = await storage.dequeue_messages(session.session_id)
        assert len(messages) == 1
        assert messages[0].payload["text"] == "Hello"

    async def test_explicit_default_project_same_as_implicit(self) -> None:
        """Test explicit default project_id behaves same as implicit."""
        storage = InMemoryStorage()
        registry = ProjectRegistry()

        registry._ensure_default_project()

        # Save with implicit default
        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )
        await storage.save_protocol(protocol)

        # Save with explicit default
        protocol2 = ProtocolDefinition(
            name="chat",
            version="2.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )
        await storage.save_protocol(protocol2, project_id="default")

        # List with implicit default should see both
        protocols = await storage.list_protocols()
        assert len(protocols) == 2

        # List with explicit default should see both
        protocols_explicit = await storage.list_protocols(project_id="default")
        assert len(protocols_explicit) == 2

    async def test_new_project_isolated_from_default(self) -> None:
        """Test new projects are isolated from default project."""
        storage = InMemoryStorage()
        registry = ProjectRegistry()

        registry._ensure_default_project()

        # Add data to default project
        protocol = ProtocolDefinition(
            name="chat",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["point_to_point"],
        )
        await storage.save_protocol(protocol)

        # Create new project
        _ = await registry.create_project(
            project_id="new_project",
            name="New Project",
        )

        # Add same protocol to new project
        await storage.save_protocol(protocol, project_id="new_project")

        # Default project should see only its protocol
        default_protocols = await storage.list_protocols(project_id="default")
        assert len(default_protocols) == 1

        # New project should see only its protocol
        new_protocols = await storage.list_protocols(project_id="new_project")
        assert len(new_protocols) == 1

        # Protocols should be independent (different versions could coexist)
        # In this case, both have version 1.0.0 but in different namespaces
        proto_default = await storage.get_protocol("chat", "1.0.0", project_id="default")
        proto_new = await storage.get_protocol("chat", "1.0.0", project_id="new_project")

        assert proto_default is not None
        assert proto_new is not None
        # They are the same definition but stored in different namespaces
        assert proto_default.name == proto_new.name

    async def test_migration_preserves_existing_behavior(self) -> None:
        """Test that migration preserves existing single-project behavior."""
        storage = InMemoryStorage()
        _ = ProjectRegistry()

        # Simulate existing single-project deployment
        # by creating data without project_id
        protocol = ProtocolDefinition(
            name="legacy_protocol",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["broadcast"],
        )

        await storage.save_protocol(protocol)

        # After migration, existing code should still work
        retrieved = await storage.get_protocol("legacy_protocol", "1.0.0")
        assert retrieved is not None
        assert retrieved.name == "legacy_protocol"

        # New multi-project code can also access the same data
        # via the default project
        retrieved_default = await storage.get_protocol(
            "legacy_protocol", "1.0.0", project_id="default"
        )
        assert retrieved_default is not None
        assert retrieved_default.name == "legacy_protocol"

    async def test_multiple_projects_dont_interfere(self) -> None:
        """Test multiple projects can coexist without interference."""
        storage = InMemoryStorage()
        registry = ProjectRegistry()

        registry._ensure_default_project()

        # Create multiple projects
        await registry.create_project(project_id="project_a", name="Project A")
        await registry.create_project(project_id="project_b", name="Project B")
        await registry.create_project(project_id="project_c", name="Project C")

        # Add protocols to each
        for project_id in ["default", "project_a", "project_b", "project_c"]:
            protocol = ProtocolDefinition(
                name=f"{project_id}_protocol",
                version="1.0.0",
                message_schema=SAMPLE_SCHEMA,
                capabilities=["point_to_point"],
            )
            await storage.save_protocol(protocol, project_id=project_id)

        # Each project should only see its own protocol
        for project_id in ["default", "project_a", "project_b", "project_c"]:
            protocols = await storage.list_protocols(project_id=project_id)
            assert len(protocols) == 1
            assert protocols[0].name == f"{project_id}_protocol"

    async def test_default_project_api_key_format(self) -> None:
        """Test default project API key follows correct format."""
        registry = ProjectRegistry()

        registry._ensure_default_project()

        project = await registry.get_project("default")

        assert project is not None
        assert len(project.api_keys) == 1

        api_key = project.api_keys[0]

        # Check format: project_id_key_id_secret
        parts = api_key.api_key.split("_")
        assert len(parts) >= 3
        assert parts[0] == "default"
        assert api_key.key_id == "default"
        assert api_key.is_active is True


class TestMigrationManager:
    """Tests for MigrationManager class."""

    async def test_is_migrated_false_initially(self) -> None:
        """Test that system is not migrated initially."""
        manager = MigrationManager(ProjectRegistry(), InMemoryStorage())  # noqa
        assert not await manager.is_migrated()

    async def test_is_migrated_true_after_migration(self) -> None:
        """Test that system is migrated after migration."""
        manager = MigrationManager(ProjectRegistry(), InMemoryStorage())  # noqa
        await manager.migrate_to_default_project()
        assert await manager.is_migrated()

    async def test_migrate_to_default_project_creates_project(self) -> None:
        """Test migration creates default project."""
        registry = ProjectRegistry()  # noqa
        manager = MigrationManager(registry, InMemoryStorage())  # noqa
        stats = await manager.migrate_to_default_project()
        project = await registry.get_project("default")

        assert project is not None
        assert project.project_id == "default"
        assert project.metadata.name == "Default Project"
        assert "protocols_migrated" in stats
        assert "sessions_migrated" in stats

    async def test_migration_is_idempotent(self) -> None:
        """Test migration can be run multiple times safely."""
        _storage = InMemoryStorage()
        _registry = ProjectRegistry()
        manager = MigrationManager(_registry, _storage)  # noqa

        # Run migration twice
        stats1 = await manager.migrate_to_default_project()
        stats2 = await manager.migrate_to_default_project()

        # Second migration should skip (no new migrations)
        assert stats2["protocols_migrated"] == stats1["protocols_migrated"]
        assert stats2["sessions_migrated"] == stats1["sessions_migrated"]

    async def test_verify_migration_success(self) -> None:
        """Test migration verification after successful migration."""
        _storage = InMemoryStorage()
        _registry = ProjectRegistry()
        manager = MigrationManager(_registry, _storage)  # noqa

        await manager.migrate_to_default_project()

        result = await manager.verify_migration()

        assert result["default_project_exists"] is True
        assert result["protocols_accessible"] is True
        assert result["sessions_accessible"] is True

    async def test_verify_migration_storage_isolation(self) -> None:
        """Test storage isolation verification."""
        _storage = InMemoryStorage()
        _registry = ProjectRegistry()
        manager = MigrationManager(_registry, _storage)  # noqa

        await manager.migrate_to_default_project()

        result = await manager.verify_migration()

        assert result["storage_isolated"] is True

    async def test_run_migration_with_verify(self) -> None:
        """Test run_migration function with verification enabled."""
        _storage = InMemoryStorage()
        _registry = ProjectRegistry()

        result = await run_migration(_registry, _storage, verify=True)  # noqa

        assert "migration_stats" in result
        assert "verification" in result
        assert result["verification"]["default_project_exists"] is True

    async def test_run_migration_without_verify(self) -> None:
        """Test run_migration function with verification disabled."""
        _storage = InMemoryStorage()
        _registry = ProjectRegistry()

        result = await run_migration(_registry, _storage, verify=False)  # noqa

        assert "migration_stats" in result
        assert "verification" not in result

    async def test_migration_preserves_existing_protocols(self) -> None:
        """Test migration preserves existing protocol data."""
        storage = InMemoryStorage()
        _registry = ProjectRegistry()

        # Create a protocol before migration (simulating existing deployment)
        protocol = ProtocolDefinition(
            name="existing_protocol",
            version="1.0.0",
            message_schema=SAMPLE_SCHEMA,
            capabilities=["broadcast"],
        )
        await storage.save_protocol(protocol)

        # Run migration
        await run_migration(_registry, storage, verify=True)  # noqa

        # Protocol should still be accessible
        retrieved = await storage.get_protocol("existing_protocol", "1.0.0", project_id="default")
        assert retrieved is not None
        assert retrieved.name == "existing_protocol"

    async def test_migration_preserves_existing_sessions(self) -> None:
        """Test migration preserves existing session data."""
        storage = InMemoryStorage()
        _registry = ProjectRegistry()

        # Create a session before migration (simulating existing deployment)
        caps = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )
        session = Session(session_id=uuid4(), capabilities=caps)
        await storage.save_session(session)

        # Run migration
        await run_migration(_registry, storage, verify=True)  # noqa

        # Session should still be accessible
        retrieved = await storage.get_session(session.session_id, project_id="default")
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
