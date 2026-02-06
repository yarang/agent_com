#!/usr/bin/env python
"""
Migration script to add ProjectApiKeyDB table.

This script creates the project_api_keys table for ProjectRegistry persistence.

Usage:
    python scripts/migrate_project_api_key_table.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_comm_core.db.database import get_engine
from agent_comm_core.db.models.project_api_key import ProjectApiKeyDB


async def migrate():
    """Run the migration to add project_api_keys table."""
    import os

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent_comm.db")

    print(f"Using database: {database_url}")

    # Create engine
    engine = get_engine(database_url, echo=True)

    try:
        async with engine.begin() as conn:
            print("\n=== Creating project_api_keys table ===")
            await conn.run_sync(
                lambda sync_conn: ProjectApiKeyDB.__table__.create(sync_conn, checkfirst=True)
            )
            print("✓ Created project_api_keys table")
            print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        from agent_comm_core.db.database import close_db

        await close_db()


if __name__ == "__main__":
    asyncio.run(migrate())
