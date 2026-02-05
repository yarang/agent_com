"""
User repository for database operations.

Provides database access layer for UserDB model.
"""

import json
from uuid import UUID

from sqlalchemy import ScalarResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.user import UserDB
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase


class UserRepository(SQLAlchemyRepositoryBase[UserDB]):
    """
    Repository for user database operations.

    Provides CRUD operations for UserDB entities.
    Extends the base repository with user specific operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, UserDB)

    # ========================================================================
    # User Specific Operations
    # ========================================================================

    async def create(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = "user",
        permissions: list[str] | None = None,
        full_name: str | None = None,
    ) -> UserDB:
        """
        Create a new user.

        Args:
            username: Unique username
            email: Unique email address
            password_hash: Argon2 hashed password
            role: User role (default: "user")
            permissions: Optional list of permissions
            full_name: Optional full name

        Returns:
            Created user instance
        """
        return await super().create(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
            is_superuser=False,
            permissions=json.dumps(permissions) if permissions else None,
            full_name=full_name,
        )

    async def get_by_username(self, username: str) -> UserDB | None:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User instance or None
        """
        result = await self._session.execute(select(UserDB).where(UserDB.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserDB | None:
        """
        Get user by email.

        Args:
            email: Email address

        Returns:
            User instance or None
        """
        result = await self._session.execute(select(UserDB).where(UserDB.email == email))
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> ScalarResult[UserDB]:
        """
        List users with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            is_active: Optional active status filter

        Returns:
            Scalar result of users
        """
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active

        return await super().list_all(limit=limit, offset=offset, filters=filters)

    async def update_password(self, user_id: UUID, password_hash: str) -> bool:
        """
        Update user password.

        Args:
            user_id: User UUID
            password_hash: New password hash

        Returns:
            True if updated, False if user not found
        """
        result = await self._session.execute(
            update(UserDB).where(UserDB.id == user_id).values(password_hash=password_hash)
        )
        return result.rowcount > 0

    async def set_active_status(self, user_id: UUID, is_active: bool) -> bool:
        """
        Set user active status.

        Args:
            user_id: User UUID
            is_active: Active status

        Returns:
            True if updated, False if user not found
        """
        result = await self._session.execute(
            update(UserDB).where(UserDB.id == user_id).values(is_active=is_active)
        )
        return result.rowcount > 0

    async def username_exists(self, username: str) -> bool:
        """
        Check if username exists.

        Args:
            username: Username to check

        Returns:
            True if username exists
        """
        result = await self._session.execute(select(UserDB.id).where(UserDB.username == username))
        return result.scalar_one_or_none() is not None

    async def email_exists(self, email: str) -> bool:
        """
        Check if email exists.

        Args:
            email: Email to check

        Returns:
            True if email exists
        """
        result = await self._session.execute(select(UserDB.id).where(UserDB.email == email))
        return result.scalar_one_or_none() is not None
