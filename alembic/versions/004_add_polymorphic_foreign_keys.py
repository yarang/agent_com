"""
Add polymorphic foreign keys and optimize schema.

This migration adds polymorphic foreign keys to ChatMessageDB and TaskDB,
enabling proper referential integrity between users/agents and messages/tasks.

Revision ID: 004_add_polymorphic_foreign_keys
Revises: 003_add_project_api_keys_table
Create Date: 2026-02-07

Changes:
- Add user_sender_id and agent_sender_id columns to chat_messages
- Add user_assigned_to and agent_assigned_to columns to tasks
- Make tasks.created_by nullable for SET NULL on delete
- Add composite indexes for query optimization
- Add CHECK constraint to chat_participants for mutual exclusivity
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic
revision = "004_add_polymorphic_foreign_keys"
down_revision = "003_add_project_api_keys_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add polymorphic foreign keys and optimize schema."""
    # Get database connection
    conn = op.get_bind()

    # Check if using SQLite
    is_sqlite = conn.dialect.name == "sqlite"

    # ===== ChatMessageDB changes =====

    # Add new polymorphic sender columns
    if is_sqlite:
        # SQLite: Add columns with SQLite syntax
        op.add_column(
            "chat_messages",
            sa.Column(
                "user_sender_id",
                sa.Uuid(),
                nullable=True,
                default=None,
            ),
        )
        op.add_column(
            "chat_messages",
            sa.Column(
                "agent_sender_id",
                sa.Uuid(),
                nullable=True,
                default=None,
            ),
        )
    else:
        # PostgreSQL: Add columns with PostgreSQL syntax
        op.execute(
            """
            ALTER TABLE chat_messages
            ADD COLUMN user_sender_id UUID NULL DEFAULT NULL,
            ADD COLUMN agent_sender_id UUID NULL DEFAULT NULL
            """
        )

    # Create foreign keys for new columns
    if is_sqlite:
        # SQLite doesn't support ALTER TABLE ADD CONSTRAINT in the same way
        # We'll need to recreate the table, but for now skip FK creation
        pass
    else:
        op.create_foreign_key(
            "fk_chat_messages_user_sender_id",
            "chat_messages",
            "users",
            ["user_sender_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_chat_messages_agent_sender_id",
            "chat_messages",
            "agents",
            ["agent_sender_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # ===== TaskDB changes =====

    # Make created_by nullable
    if is_sqlite:
        # SQLite: Need to recreate table to change NOT NULL constraint
        # For SQLite, we'll just ensure the column allows NULL
        # Since SQLite doesn't enforce NOT NULL in the same way
        pass
    else:
        op.execute("ALTER TABLE tasks ALTER COLUMN created_by DROP NOT NULL")

    # Add new polymorphic assignment columns
    if is_sqlite:
        op.add_column(
            "tasks",
            sa.Column(
                "user_assigned_to",
                sa.Uuid(),
                nullable=True,
                default=None,
            ),
        )
        op.add_column(
            "tasks",
            sa.Column(
                "agent_assigned_to",
                sa.Uuid(),
                nullable=True,
                default=None,
            ),
        )
    else:
        op.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN user_assigned_to UUID NULL DEFAULT NULL,
            ADD COLUMN agent_assigned_to UUID NULL DEFAULT NULL
            """
        )

    # Create foreign keys for new columns
    if is_sqlite:
        pass  # SQLite limitation
    else:
        op.create_foreign_key(
            "fk_tasks_user_assigned_to",
            "tasks",
            "users",
            ["user_assigned_to"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_tasks_agent_assigned_to",
            "tasks",
            "agents",
            ["agent_assigned_to"],
            ["id"],
            ondelete="SET NULL",
        )

    # ===== Composite indexes for query optimization =====

    # ChatMessageDB indexes
    if is_sqlite:
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_chat_messages_room_sender
                ON chat_messages(room_id, sender_type)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_chat_messages_room_created
                ON chat_messages(room_id, created_at DESC)
            """)
        )
    else:
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_chat_messages_room_sender
                ON chat_messages(room_id, sender_type)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_chat_messages_room_created
                ON chat_messages(room_id, created_at DESC)
            """)
        )

    # TaskDB indexes
    if is_sqlite:
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_tasks_project_status
                ON tasks(project_id, status)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_tasks_user_assigned_status
                ON tasks(user_assigned_to, status)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_tasks_agent_assigned_status
                ON tasks(agent_assigned_to, status)
            """)
        )
    else:
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_tasks_project_status
                ON tasks(project_id, status)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_tasks_user_assigned_status
                ON tasks(user_assigned_to, status)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_tasks_agent_assigned_status
                ON tasks(agent_assigned_to, status)
            """)
        )

    # ===== ChatParticipantDB CHECK constraint =====
    # Note: SQLite's CHECK constraint support is limited
    # This constraint ensures exactly one of agent_id or user_id is set
    # For SQLite, we skip the constraint (enforced at application level)
    if not is_sqlite:
        # PostgreSQL: Check constraint syntax
        conn.execute(
            text("""
                ALTER TABLE chat_participants
                ADD CONSTRAINT IF NOT EXISTS ck_participant_exactly_one
                CHECK ((agent_id IS NOT NULL AND user_id IS NULL) OR
                       (agent_id IS NULL AND user_id IS NOT NULL))
            """)
        )

    conn.commit()


def downgrade() -> None:
    """Revert polymorphic foreign keys changes."""
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # Drop indexes
    if is_sqlite:
        conn.execute(text("DROP INDEX IF EXISTS ix_chat_messages_room_sender"))
        conn.execute(text("DROP INDEX IF EXISTS ix_chat_messages_room_created"))
        conn.execute(text("DROP INDEX IF EXISTS ix_tasks_project_status"))
        conn.execute(text("DROP INDEX IF EXISTS ix_tasks_user_assigned_status"))
        conn.execute(text("DROP INDEX IF EXISTS ix_tasks_agent_assigned_status"))
    else:
        conn.execute(text("DROP INDEX IF EXISTS ix_chat_messages_room_sender"))
        conn.execute(text("DROP INDEX IF EXISTS ix_chat_messages_room_created"))
        conn.execute(text("DROP INDEX IF EXISTS ix_tasks_project_status"))
        conn.execute(text("DROP INDEX IF EXISTS ix_tasks_user_assigned_status"))
        conn.execute(text("DROP INDEX IF EXISTS ix_tasks_agent_assigned_status"))

    # Drop CHECK constraint
    if is_sqlite:
        # SQLite doesn't support dropping constraints directly
        pass
    else:
        conn.execute(
            text(
                "ALTER TABLE chat_participants DROP CONSTRAINT IF EXISTS ck_participant_exactly_one"
            )
        )

    # Drop TaskDB columns
    if is_sqlite:
        op.drop_column("tasks", "agent_assigned_to")
        op.drop_column("tasks", "user_assigned_to")
    else:
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS agent_assigned_to")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS user_assigned_to")

    # Make created_by NOT NULL again (revert)
    if not is_sqlite:
        op.execute("ALTER TABLE tasks ALTER COLUMN created_by SET NOT NULL")

    # Drop ChatMessageDB columns
    if is_sqlite:
        op.drop_column("chat_messages", "agent_sender_id")
        op.drop_column("chat_messages", "user_sender_id")
    else:
        op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS agent_sender_id")
        op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS user_sender_id")

    conn.commit()
