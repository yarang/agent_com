"""
Migration module for single-project to multi-project transition.

This module provides migration utilities to ensure smooth transition
from single-project deployments to multi-project support while
maintaining backward compatibility.
"""

from mcp_broker.core.logging import get_logger
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.project.registry import ProjectRegistry
from mcp_broker.storage.interface import StorageBackend

logger = get_logger(__name__)


class MigrationManager:
    """
    Manages migration from single-project to multi-project deployments.

    The migration process ensures backward compatibility by creating a
    "default" project and migrating all existing resources (protocols,
    sessions, messages) to this project namespace.
    """

    DEFAULT_PROJECT_ID = "default"
    DEFAULT_PROJECT_NAME = "Default Project"
    DEFAULT_PROJECT_DESCRIPTION = "Default project for backward compatibility"

    def __init__(self, registry: ProjectRegistry, storage: StorageBackend) -> None:
        """Initialize migration manager.

        Args:
            registry: Project registry instance
            storage: Storage backend instance
        """
        self.registry = registry
        self.storage = storage

    async def is_migrated(self) -> bool:
        """Check if the system has already been migrated.

        Returns:
            True if default project exists, False otherwise
        """
        project = await self.registry.get_project(self.DEFAULT_PROJECT_ID)
        return project is not None

    async def migrate_to_default_project(self) -> dict[str, int]:
        """
        Migrate existing single-project deployment to multi-project.

        This process:
        1. Creates the "default" project if it doesn't exist
        2. Migrates all existing protocols to default project
        3. Migrates all existing sessions to default project
        4. Verifies data integrity

        Returns:
            Dictionary with migration statistics:
            - protocols_migrated: Number of protocols migrated
            - sessions_migrated: Number of sessions migrated
            - messages_migrated: Number of messages migrated
        """
        if await self.is_migrated():
            logger.info("System already migrated, skipping migration")
            return {"protocols_migrated": 0, "sessions_migrated": 0, "messages_migrated": 0}

        logger.info("Starting migration to multi-project mode")

        # Step 1: Ensure default project exists
        await self._ensure_default_project()

        # Step 2: Migrate protocols (they're already using implicit default)
        protocols_migrated = await self._migrate_protocols()

        # Step 3: Migrate sessions (they're already using implicit default)
        sessions_migrated = await self._migrate_sessions()

        # Step 4: Messages are implicitly migrated as part of session queues
        messages_migrated = 0  # Messages use session-scoped queues

        logger.info(
            "Migration completed",
            extra={
                "context": {
                    "protocols_migrated": protocols_migrated,
                    "sessions_migrated": sessions_migrated,
                    "messages_migrated": messages_migrated,
                }
            },
        )

        return {
            "protocols_migrated": protocols_migrated,
            "sessions_migrated": sessions_migrated,
            "messages_migrated": messages_migrated,
        }

    async def _ensure_default_project(self) -> None:
        """Ensure default project exists in the registry."""
        if await self.is_migrated():
            return

        # Create default project
        project = await self.registry.create_project(
            project_id=self.DEFAULT_PROJECT_ID,
            name=self.DEFAULT_PROJECT_NAME,
            description=self.DEFAULT_PROJECT_DESCRIPTION,
        )

        logger.info(
            f"Created default project: {self.DEFAULT_PROJECT_ID}",
            extra={"context": {"project_id": self.DEFAULT_PROJECT_ID}},
        )

    async def _migrate_protocols(self) -> int:
        """Migrate existing protocols to default project.

        Note: In the current implementation, protocols are already
        stored with project_id="default" by default, so this is
        primarily a verification step.

        Returns:
            Number of protocols in default project
        """
        protocols = await self.storage.list_protocols(project_id=self.DEFAULT_PROJECT_ID)
        count = len(protocols)

        logger.info(
            f"Verified {count} protocols in default project",
            extra={"context": {"count": count}},
        )

        return count

    async def _migrate_sessions(self) -> int:
        """Migrate existing sessions to default project.

        Note: In the current implementation, sessions are already
        stored with project_id="default" by default, so this is
        primarily a verification step.

        Returns:
            Number of sessions in default project
        """
        sessions = await self.storage.list_sessions(project_id=self.DEFAULT_PROJECT_ID)
        count = len(sessions)

        logger.info(
            f"Verified {count} sessions in default project",
            extra={"context": {"count": count}},
        )

        return count

    async def verify_migration(self) -> dict[str, bool]:
        """Verify that migration was successful.

        Returns:
            Dictionary with verification results:
            - default_project_exists: True if default project exists
            - protocols_accessible: True if protocols are accessible
            - sessions_accessible: True if sessions are accessible
            - storage_isolated: True if storage is properly isolated
        """
        results: dict[str, bool] = {}

        # Check default project exists
        results["default_project_exists"] = await self.is_migrated()

        # Check protocols are accessible
        try:
            protocols = await self.storage.list_protocols(project_id=self.DEFAULT_PROJECT_ID)
            results["protocols_accessible"] = True
        except Exception as e:
            logger.warning(f"Protocol verification failed: {e}")
            results["protocols_accessible"] = False

        # Check sessions are accessible
        try:
            sessions = await self.storage.list_sessions(project_id=self.DEFAULT_PROJECT_ID)
            results["sessions_accessible"] = True
        except Exception as e:
            logger.warning(f"Session verification failed: {e}")
            results["sessions_accessible"] = False

        # Check storage isolation (test project isolation)
        try:
            # Create a test project
            test_project = await self.registry.create_project(
                project_id="migration_verification_test",
                name="Migration Verification Test",
            )

            # Add a test protocol to test project
            test_protocol = ProtocolDefinition(
                name="test_protocol",
                version="1.0.0",
                message_schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                },
                capabilities=["test"],
            )
            await self.storage.save_protocol(
                test_protocol, project_id="migration_verification_test"
            )

            # Verify isolation: default project shouldn't see test protocol
            default_protocols = await self.storage.list_protocols(
                project_id=self.DEFAULT_PROJECT_ID
            )
            test_protocols = await self.storage.list_protocols(
                project_id="migration_verification_test"
            )

            results["storage_isolated"] = (
                len(default_protocols) == 0
                or all(p.name != "test_protocol" for p in default_protocols)
            ) and len(test_protocols) == 1

            # Clean up test project
            await self.storage.delete_protocol(
                "test_protocol", "1.0.0", project_id="migration_verification_test"
            )
            await self.registry.delete_project("migration_verification_test")

        except Exception as e:
            logger.warning(f"Storage isolation verification failed: {e}")
            results["storage_isolated"] = False

        return results


async def run_migration(
    registry: ProjectRegistry, storage: StorageBackend, verify: bool = True
) -> dict[str, int | dict[str, bool]]:
    """
    Run migration from single-project to multi-project mode.

    Args:
        registry: Project registry instance
        storage: Storage backend instance
        verify: Whether to verify migration after completion

    Returns:
        Dictionary with migration statistics and verification results
    """
    manager = MigrationManager(registry, storage)

    # Run migration
    stats = await manager.migrate_to_default_project()

    result: dict[str, int | dict[str, bool]] = {"migration_stats": stats}

    # Verify if requested
    if verify:
        verification = await manager.verify_migration()
        result["verification"] = verification

    return result
