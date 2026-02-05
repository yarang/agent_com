"""
Agent API key repository for database operations.

Provides database access layer for AgentApiKeyDB model.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import ScalarResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent_api_key import AgentApiKeyDB
from agent_comm_core.models.common import ActorType as CreatorType
from agent_comm_core.models.common import KeyStatus
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase


class AgentApiKeyRepository(SQLAlchemyRepositoryBase[AgentApiKeyDB]):
    """
    Repository for agent API key database operations.

    Provides CRUD operations for AgentApiKeyDB entities.
    Extends the base repository with agent API key specific operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, AgentApiKeyDB)

    # ========================================================================
    # Agent API Key Specific Operations
    # ========================================================================

    async def create(
        self,
        project_id: UUID,
        agent_id: UUID,
        key_id: str,
        api_key_hash: str,
        key_prefix: str,
        capabilities: list[str],
        created_by_type: str = CreatorType.USER,  # Using CreatorType from DB model
        created_by_id: UUID | None = None,
        expires_at: str | None = None,
    ) -> AgentApiKeyDB:
        """
        Create a new agent API key.

        Args:
            project_id: Project UUID
            agent_id: Agent UUID
            key_id: Human-readable key identifier
            api_key_hash: SHA-256 hash of the API key
            key_prefix: Key prefix for identification
            capabilities: List of agent capabilities
            created_by_type: Type of creator (user/agent/system)
            created_by_id: UUID of the creator
            expires_at: Optional expiration timestamp

        Returns:
            Created agent API key instance
        """
        return await super().create(
            project_id=project_id,
            agent_id=agent_id,
            key_id=key_id,
            api_key_hash=api_key_hash,
            key_prefix=key_prefix,
            capabilities=capabilities,
            status=KeyStatus.ACTIVE,
            expires_at=expires_at,
            created_by_type=created_by_type,
            created_by_id=created_by_id or uuid4(),
        )

    async def get_by_key_id(self, key_id: str) -> AgentApiKeyDB | None:
        """
        Get agent API key by human-readable key ID.

        Args:
            key_id: Key identifier

        Returns:
            Agent API key instance or None
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.key_id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, api_key_hash: str) -> AgentApiKeyDB | None:
        """
        Get agent API key by hash.

        Args:
            api_key_hash: SHA-256 hash of the API key

        Returns:
            Agent API key instance or None
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.api_key_hash == api_key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_agent_id(self, agent_id: UUID) -> list[AgentApiKeyDB]:
        """
        Get all API keys for an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            List of agent API key instances
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent_id)
        )
        return list(result.scalars().all())

    async def get_by_project_id(self, project_id: UUID) -> list[AgentApiKeyDB]:
        """
        Get all API keys for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of agent API key instances
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.project_id == project_id)
        )
        return list(result.scalars().all())

    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> ScalarResult[AgentApiKeyDB]:
        """
        List active API keys.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Scalar result of agent API keys
        """
        query = (
            select(AgentApiKeyDB)
            .where(AgentApiKeyDB.status == KeyStatus.ACTIVE)
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(query)
        return result.scalars()

    async def revoke(self, key_id: UUID) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: API key UUID

        Returns:
            True if revoked, False if not found
        """
        result = await self._session.execute(
            update(AgentApiKeyDB).where(AgentApiKeyDB.id == key_id).values(status=KeyStatus.REVOKED)
        )
        return result.rowcount > 0

    async def update_last_used(self, key_id: UUID) -> bool:
        """
        Update the last used timestamp (via updated_at).

        Args:
            key_id: API key UUID

        Returns:
            True if updated, False if not found
        """
        result = await self._session.execute(
            update(AgentApiKeyDB)
            .where(AgentApiKeyDB.id == key_id)
            .values(updated_at=datetime.now(UTC))
        )
        return result.rowcount > 0

    async def agent_exists_in_project(self, project_id: UUID, agent_id: UUID) -> bool:
        """
        Check if agent key exists in project.

        Args:
            project_id: Project UUID
            agent_id: Agent UUID

        Returns:
            True if exists
        """
        result = await self._session.execute(
            select(AgentApiKeyDB.id).where(
                AgentApiKeyDB.project_id == project_id,
                AgentApiKeyDB.agent_id == agent_id,
            )
        )
        return result.scalar_one_or_none() is not None
