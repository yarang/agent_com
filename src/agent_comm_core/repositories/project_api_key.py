"""
Project API Key repository for database operations.

Provides database access layer for ProjectApiKeyDB model
used by the MCP broker ProjectRegistry system.
"""

from uuid import UUID

from sqlalchemy import ScalarResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.project_api_key import ProjectApiKeyDB
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase


class ProjectApiKeyRepository(SQLAlchemyRepositoryBase[ProjectApiKeyDB]):
    """
    Repository for project API key database operations.

    Provides CRUD operations for ProjectApiKeyDB entities.
    Extends the base repository with project API key specific operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, ProjectApiKeyDB)

    # ========================================================================
    # Project API Key Specific Operations
    # ========================================================================

    async def create(
        self,
        project_uuid: UUID,
        key_id: str,
        api_key_hash: str,
        key_prefix: str,
        created_by_id: UUID | None = None,
    ) -> ProjectApiKeyDB:
        """
        Create a new project API key.

        Args:
            project_uuid: Project UUID (foreign key to projects.id)
            key_id: Human-readable key identifier
            api_key_hash: SHA-256 hash of the API key
            key_prefix: Key prefix for identification (first 20 chars)
            created_by_id: UUID of the user who created the key

        Returns:
            Created project API key instance
        """
        return await super().create(
            project_uuid=project_uuid,
            key_id=key_id,
            api_key_hash=api_key_hash,
            key_prefix=key_prefix,
            is_active=True,
            created_by_id=created_by_id,
        )

    async def get_by_key_id(self, key_id: str) -> ProjectApiKeyDB | None:
        """
        Get project API key by human-readable key ID.

        Args:
            key_id: Key identifier

        Returns:
            Project API key instance or None
        """
        result = await self._session.execute(
            select(ProjectApiKeyDB).where(ProjectApiKeyDB.key_id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, api_key_hash: str) -> ProjectApiKeyDB | None:
        """
        Get project API key by hash.

        Args:
            api_key_hash: SHA-256 hash of the API key

        Returns:
            Project API key instance or None
        """
        result = await self._session.execute(
            select(ProjectApiKeyDB).where(ProjectApiKeyDB.api_key_hash == api_key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_project_uuid(self, project_uuid: UUID) -> list[ProjectApiKeyDB]:
        """
        Get all API keys for a project.

        Args:
            project_uuid: Project UUID

        Returns:
            List of project API key instances
        """
        result = await self._session.execute(
            select(ProjectApiKeyDB).where(ProjectApiKeyDB.project_uuid == project_uuid)
        )
        return list(result.scalars().all())

    async def list_active(
        self,
        project_uuid: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ScalarResult[ProjectApiKeyDB]:
        """
        List active API keys, optionally filtered by project.

        Args:
            project_uuid: Optional project UUID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Scalar result of project API keys
        """
        query = select(ProjectApiKeyDB).where(ProjectApiKeyDB.is_active)

        if project_uuid:
            query = query.where(ProjectApiKeyDB.project_uuid == project_uuid)

        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return result.scalars()

    async def deactivate(self, key_id: UUID) -> bool:
        """
        Deactivate an API key.

        Args:
            key_id: API key UUID

        Returns:
            True if deactivated, False if not found
        """
        result = await self._session.execute(
            update(ProjectApiKeyDB).where(ProjectApiKeyDB.id == key_id).values(is_active=False)
        )
        return result.rowcount > 0

    async def delete_by_project(self, project_uuid: UUID) -> int:
        """
        Delete all API keys for a project.

        Args:
            project_uuid: Project UUID

        Returns:
            Number of keys deleted
        """
        result = await self._session.execute(
            delete(ProjectApiKeyDB).where(ProjectApiKeyDB.project_uuid == project_uuid)
        )
        return result.rowcount

    async def key_id_exists(self, key_id: str) -> bool:
        """
        Check if a key ID exists.

        Args:
            key_id: Key identifier string

        Returns:
            True if key ID exists
        """
        result = await self._session.execute(
            select(ProjectApiKeyDB.id).where(ProjectApiKeyDB.key_id == key_id)
        )
        return result.scalar_one_or_none() is not None


__all__ = ["ProjectApiKeyRepository"]
