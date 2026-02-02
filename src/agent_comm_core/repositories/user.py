"""
User repository for database operations.

Provides database access layer for UserDB model.
"""

from uuid import UUID

from sqlalchemy import ScalarResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.user import UserDB


class UserRepository:
    """
    Repository for user database operations.

    Provides CRUD operations for UserDB entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

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
        import json

        user = UserDB(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
            is_superuser=False,
            permissions=json.dumps(permissions) if permissions else None,
            full_name=full_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: UUID) -> UserDB | None:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User instance or None
        """
        result = await self._session.execute(select(UserDB).where(UserDB.id == user_id))
        return result.scalar_one_or_none()

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
        query = select(UserDB)

        if is_active is not None:
            query = query.where(UserDB.is_active == is_active)

        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return result.scalars()

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
