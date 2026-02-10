"""
Add foreign key constraint to agent_api_keys.created_by_id.

This migration adds referential integrity between agent API keys and users
table, establishing proper ownership tracking.

SPEC: SPEC-AGENT-002 - Agent User Ownership Model

Revision ID: 002_add_agent_api_key_user_fk
Revises: 001_create_mediator_tables
Create Date: 2026-02-05

Changes:
- Validates existing created_by_id values reference valid users
- Adds foreign key constraint: agent_api_keys.created_by_id -> users.id
- Sets ON DELETE SET NULL behavior
- Handles orphaned records gracefully by setting them to NULL

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision = "002_add_agent_api_key_user_fk"
down_revision = None  # Base migration (001 was missing, keeping as base)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add foreign key constraint to agent_api_keys.created_by_id."""
    # Get the database connection
    conn = op.get_bind()

    # Step 1: Validate existing data and identify orphaned records
    result = conn.execute(
        sa.text("""
        SELECT COUNT(*) FROM agent_api_keys aak
        LEFT JOIN users u ON aak.created_by_id = u.id
        WHERE u.id IS NULL AND aak.created_by_id IS NOT NULL
    """)
    )
    orphaned_count = result.scalar()

    if orphaned_count > 0:
        # Log warning and set orphaned records to NULL
        print(
            f"Warning: Found {orphaned_count} orphaned agent_api_keys records. Setting created_by_id to NULL."
        )
        conn.execute(
            sa.text("""
            UPDATE agent_api_keys
            SET created_by_id = NULL
            WHERE created_by_id IS NOT NULL
            AND created_by_id NOT IN (SELECT id FROM users)
        """)
        )
        print(f"Set {orphaned_count} orphaned record(s) to NULL")

    # Step 2: Add foreign key constraint
    op.create_foreign_key(
        "fk_agent_api_keys_created_by_id_users",
        "agent_api_keys",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Step 3: Create index on created_by_id for query performance
    op.create_index(
        "idx_agent_api_keys_created_by_id", "agent_api_keys", ["created_by_id"], unique=False
    )


def downgrade() -> None:
    """Remove foreign key constraint and index."""
    # Drop the foreign key constraint
    op.drop_constraint(
        "fk_agent_api_keys_created_by_id_users", "agent_api_keys", type_="foreignkey"
    )

    # Drop the index
    op.drop_index("idx_agent_api_keys_created_by_id", table_name="agent_api_keys")
