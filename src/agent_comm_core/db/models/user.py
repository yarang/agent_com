"""
User database model for OAuth-based human accounts.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
        Uuid,
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
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    sent_messages = relationship(
        "ChatMessageDB",
        foreign_keys="ChatMessageDB.user_sender_id",
        back_populates="user_sender",
        lazy="selectin",
    )
    assigned_tasks = relationship(
        "TaskDB",
        foreign_keys="TaskDB.user_assigned_to",
        back_populates="assigned_user",
        lazy="selectin",
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
