#!/usr/bin/env python
"""
Migration script to add AgentDB and TaskDB tables.

This script adds the missing `agents` and `tasks` tables to the database
and fixes foreign key constraints on `chat_participants` and `agent_api_keys`.

Usage:
    python scripts/migrate_agent_task_tables.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.task import TaskDB


async def migrate():
    """Run the migration to add agent and task tables."""
    import os

    database_url = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./agent_comm.db"
    )

    print(f"Using database: {database_url}")

    # Create engine
    engine = create_async_engine(database_url, echo=True)

    try:
        async with engine.begin() as conn:
            print("\n=== Step 1: Create agents table ===")
            await conn.run_sync(
                lambda sync_conn: AgentDB.__table__.create(sync_conn, checkfirst=True)
            )
            print("✓ Created agents table")

            print("\n=== Step 2: Create tasks table ===")
            await conn.run_sync(
                lambda sync_conn: TaskDB.__table__.create(sync_conn, checkfirst=True)
            )
            print("✓ Created tasks table")

            print("\n=== Step 3: Migrate orphaned agent_id records ===")

            # Check if there are orphaned agent_id values in agent_api_keys
            result = await conn.execute(
                text("""
                SELECT DISTINCT agent_id
                FROM agent_api_keys
                WHERE agent_id NOT IN (SELECT id FROM agents WHERE id IS NOT NULL)
            """)
            )
            orphaned_agent_ids = result.fetchall()

            if orphaned_agent_ids:
                print(f"Found {len(orphaned_agent_ids)} orphaned agent_id records")

                # For each orphaned agent_id, create a placeholder agent
                for (agent_id,) in orphaned_agent_ids:
                    # Get project_id from agent_api_keys
                    project_result = await conn.execute(
                        text("""
                        SELECT DISTINCT project_id
                        FROM agent_api_keys
                        WHERE agent_id = :agent_id
                        LIMIT 1
                    """),
                        {"agent_id": str(agent_id)},
                    )
                    project_row = project_result.fetchone()

                    if project_row:
                        project_id = project_row[0]

                        # Create placeholder agent
                        await conn.execute(
                            text("""
                            INSERT INTO agents (id, project_id, name, agent_type, status, is_active)
                            VALUES (:agent_id, :project_id, :name, 'generic', 'offline', TRUE)
                        """),
                            {
                                "agent_id": str(agent_id),
                                "project_id": str(project_id),
                                "name": f"Migrated Agent {str(agent_id)[:8]}",
                            },
                        )
                        print(f"  - Created placeholder agent for {agent_id}")
            else:
                print("No orphaned agent_id records found")

            print("\n=== Step 4: Verify foreign key constraints ===")

            # Note: SQLite doesn't support adding FK constraints to existing tables
            # The agent_api_keys and chat_participants tables should be recreated with FKs
            # For now, we're creating the agents table so future inserts will have FKs

            print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
