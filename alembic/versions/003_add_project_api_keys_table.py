"""
Add project_api_keys table for MCP broker ProjectRegistry persistence.

This migration creates the project_api_keys table for storing API keys
used by the ProjectRegistry system with secure hashing.

SPEC: SPEC-PROJECT-REGISTRY-PERSISTENCE-001 - ProjectRegistry Database Persistence

Revision ID: 003_add_project_api_keys_table
Revises: 002_add_agent_api_key_user_fk
Create Date: 2026-02-06

Changes:
- Creates project_api_keys table with SHA-256 hashing for API keys
- Adds foreign key constraint to projects table (CASCADE delete)
- Adds foreign key constraint to users table (SET NULL for creator)
- Creates unique constraint on (project_uuid, key_id)
- Creates indexes for project_uuid and key_id lookups
- api_key_hash stores SHA-256 hash (full key never stored)
- key_prefix stores first 20 characters for identification

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision = "003_add_project_api_keys_table"
down_revision = "002_add_agent_api_key_user_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project_api_keys table with constraints and indexes."""
    # Create project_api_keys table
    op.create_table(
        "project_api_keys",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_uuid",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="Project UUID (foreign key to projects.id)",
        ),
        sa.Column(
            "key_id",
            sa.String(100),
            nullable=False,
            unique=True,
            index=True,
            comment="Human-readable key identifier",
        ),
        sa.Column(
            "api_key_hash",
            sa.String(255),
            nullable=False,
            unique=True,
            index=True,
            comment="SHA-256 hash of the API key",
        ),
        sa.Column(
            "key_prefix",
            sa.String(50),
            nullable=False,
            comment="First 20 characters for identification",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            default=True,
            index=True,
            comment="Whether the key is currently active",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Optional expiration timestamp",
        ),
        sa.Column(
            "created_by_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User UUID who created this key",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Creation timestamp",
        ),
        sa.UniqueConstraint(
            "project_uuid",
            "key_id",
            name="uq_project_key_id",
            comment="Ensure unique key IDs per project",
        ),
        comment="Project API keys with secure hashing for ProjectRegistry",
    )

    # Note: SQLite doesn't support COMMENT on columns/indexes
    # The above comments are documentation only


def downgrade() -> None:
    """Drop project_api_keys table."""
    op.drop_table("project_api_keys")
