"""
User database model for OAuth-based human accounts.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from agent_comm_core.db.base import Base


class UserRole(str, Enum):
    """User roles for RBAC."""

    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class UserDB(Base):
    """
    Database model for human users (OAuth-based).

    Supports OAuth 2.0 authentication with role-based access control.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Authentication fields (OAuth provider stores credentials)
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    # Profile fields
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    # Authorization fields
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # Additional permissions (JSON stored as text)
    permissions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserDB(id={self.id}, username={self.username}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def can_write(self) -> bool:
        """Check if user has write permissions."""
        return self.role in (UserRole.OWNER, UserRole.ADMIN, UserRole.USER)
