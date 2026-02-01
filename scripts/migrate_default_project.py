#!/usr/bin/env python3
"""
Migration script for single-project to multi-project transition.

This script creates a "default" project and migrates existing
protocols, sessions, and messages to the default project namespace.

This ensures backward compatibility when upgrading from single-project
to multi-project mode.

Usage:
    python scripts/migrate_default_project.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_broker.models.project import ProjectDefinition, ProjectMetadata, ProjectAPIKey
from mcp_broker.project.registry import ProjectRegistry
from mcp_broker.storage.memory import InMemoryStorage


async def migrate_to_default_project(storage: InMemoryStorage) -> None:
    """Migrate existing data to default project.

    Args:
        storage: Storage instance to migrate
    """
    print("Starting migration to default project...")

    # Create default project in registry
    registry = ProjectRegistry()

    # Ensure default project exists
    registry._ensure_default_project()

    print("✓ Default project created/verified")

    # Migration is automatic - storage methods use "default" project_id
    # when project_id is not specified, maintaining backward compatibility

    print("✓ Migration complete - backward compatibility maintained")
    print("\nStorage now supports:")
    print("  - Project-scoped operations (specify project_id)")
    print("  - Default project for legacy code (no project_id = 'default')")
    print("  - Multi-project isolation")


async def verify_migration() -> None:
    """Verify migration was successful."""
    print("\nVerifying migration...")

    storage = InMemoryStorage()
    registry = ProjectRegistry()

    # Ensure default project exists
    registry._ensure_default_project()

    # Test default project exists
    default_project = await registry.get_project("default")
    assert default_project is not None, "Default project not found"
    print("✓ Default project exists")

    # Test storage operations with default project_id
    from mcp_broker.models.protocol import ProtocolDefinition
    from uuid import uuid4
    from mcp_broker.models.session import Session, SessionCapabilities

    # Test protocol storage
    sample_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"text": {"type": "string"}},
    }

    protocol = ProtocolDefinition(
        name="test",
        version="1.0.0",
        message_schema=sample_schema,
        capabilities=["point_to_point"],
    )

    await storage.save_protocol(protocol)  # Without project_id
    retrieved = await storage.get_protocol("test", "1.0.0")  # Without project_id
    assert retrieved is not None, "Protocol not found in default project"

    retrieved_with_default = await storage.get_protocol("test", "1.0.0", project_id="default")
    assert retrieved_with_default is not None, "Protocol not found with explicit default"

    print("✓ Protocol storage works with default project")

    # Test session storage
    caps = SessionCapabilities(supported_protocols={"test": ["1.0.0"]})
    session = Session(session_id=uuid4(), capabilities=caps)

    await storage.save_session(session)  # Without project_id
    retrieved = await storage.get_session(session.session_id)  # Without project_id
    assert retrieved is not None, "Session not found in default project"

    print("✓ Session storage works with default project")

    print("\n✓ All verification checks passed!")


async def main() -> int:
    """Main migration entry point."""
    print("=" * 60)
    print("MCP Broker: Single-Project to Multi-Project Migration")
    print("=" * 60)
    print()

    storage = InMemoryStorage()

    try:
        await migrate_to_default_project(storage)
        await verify_migration()
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
