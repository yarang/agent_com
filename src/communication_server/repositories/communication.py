"""
SQLAlchemy implementation of CommunicationRepository.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_comm_core.models.communication import Communication, CommunicationCreate
from agent_comm_core.repositories.base import CommunicationRepository

from communication_server.db.communication import CommunicationDB


class SQLAlchemyCommunicationRepository(CommunicationRepository):
    """
    SQLAlchemy implementation of CommunicationRepository.

    Provides CRUD operations for communications using PostgreSQL
    with asyncpg driver.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Communication]:
        """
        Retrieve a communication by its ID.

        Args:
            id: Unique identifier of the communication

        Returns:
            The communication if found, None otherwise
        """
        result = await self._session.execute(
            select(CommunicationDB).where(CommunicationDB.id == id)
        )
        db_comm = result.scalar_one_or_none()
        return db_comm.to_pydantic() if db_comm else None

    async def create(self, data: CommunicationCreate) -> Communication:
        """
        Create a new communication.

        Args:
            data: Communication creation data

        Returns:
            The created communication
        """
        db_comm = CommunicationDB.from_pydantic(data)
        self._session.add(db_comm)
        await self._session.flush()
        return db_comm.to_pydantic()

    async def update(self, id: UUID, data: dict) -> Optional[Communication]:
        """
        Update an existing communication.

        Note: Communications are immutable after creation.
        This method is provided for interface compatibility.

        Args:
            id: Unique identifier of the communication
            data: Fields to update (ignored, communications are immutable)

        Returns:
            None (communications cannot be updated)
        """
        # Communications are log entries and should not be modified
        return None

    async def delete(self, id: UUID) -> bool:
        """
        Delete a communication by its ID.

        Args:
            id: Unique identifier of the communication

        Returns:
            True if deleted, False if not found
        """
        result = await self._session.execute(
            delete(CommunicationDB).where(CommunicationDB.id == id)
        )
        return result.rowcount > 0

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Communication]:
        """
        List all communications with pagination.

        Args:
            limit: Maximum number of communications to return
            offset: Number of communications to skip

        Returns:
            List of communications ordered by creation time (newest first)
        """
        result = await self._session.execute(
            select(CommunicationDB)
            .order_by(CommunicationDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        db_comms = result.scalars().all()
        return [comm.to_pydantic() for comm in db_comms]

    async def get_by_correlation_id(self, correlation_id: UUID) -> list[Communication]:
        """
        Retrieve all communications with a given correlation ID.

        Args:
            correlation_id: Correlation ID to filter by

        Returns:
            List of related communications ordered by creation time
        """
        result = await self._session.execute(
            select(CommunicationDB)
            .where(CommunicationDB.correlation_id == correlation_id)
            .order_by(CommunicationDB.created_at.asc())
        )
        db_comms = result.scalars().all()
        return [comm.to_pydantic() for comm in db_comms]

    async def get_by_agents(
        self,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None,
        limit: int = 100,
    ) -> list[Communication]:
        """
        Retrieve communications filtered by agent IDs.

        Args:
            from_agent: Source agent filter (optional)
            to_agent: Target agent filter (optional)
            limit: Maximum number of results

        Returns:
            List of filtered communications ordered by creation time (newest first)
        """
        conditions = []
        if from_agent:
            conditions.append(CommunicationDB.from_agent == from_agent)
        if to_agent:
            conditions.append(CommunicationDB.to_agent == to_agent)

        query = select(CommunicationDB).order_by(CommunicationDB.created_at.desc())
        if conditions:
            query = query.where(and_(*conditions))

        result = await self._session.execute(query.limit(limit))
        db_comms = result.scalars().all()
        return [comm.to_pydantic() for comm in db_comms]
