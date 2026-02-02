"""
Dependency injection for FastAPI routes.

Provides functions for injecting services and database sessions
into API route handlers.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.config import Config, get_config
from agent_comm_core.db.database import db_session
from agent_comm_core.services.communication import CommunicationService
from agent_comm_core.services.discussion import DiscussionService
from agent_comm_core.services.meeting import MeetingService
from communication_server.repositories.communication import (
    SQLAlchemyCommunicationRepository,
)
from communication_server.repositories.meeting import SQLALchemyMeetingRepository
from communication_server.websocket.manager import ConnectionManager

# Global connection manager for WebSocket
_ws_manager = ConnectionManager()


@lru_cache
def get_config_cached() -> Config:
    """
    Get the cached configuration instance.

    Returns:
        Config singleton instance
    """
    return get_config()


def get_database_url() -> str:
    """Get the database URL from configuration."""
    config = get_config()
    return config.get_database_url()


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    Get a database session for use in API routes.

    Yields:
        Async database session
    """
    database_url = get_database_url()
    async with db_session(database_url=database_url) as session:
        yield session


@lru_cache
def get_connection_manager() -> ConnectionManager:
    """
    Get the global WebSocket connection manager.

    Returns:
        Connection manager instance
    """
    return _ws_manager


async def get_communication_service(
    session: AsyncSession = Depends(get_db_session),
) -> CommunicationService:
    """
    Get a communication service instance.

    Args:
        session: Database session

    Returns:
        Communication service instance
    """
    repository = SQLAlchemyCommunicationRepository(session)
    return CommunicationService(repository)


async def get_meeting_service(
    session: AsyncSession = Depends(get_db_session),
) -> MeetingService:
    """
    Get a meeting service instance.

    Args:
        session: Database session

    Returns:
        Meeting service instance
    """
    repository = SQLALchemyMeetingRepository(session)
    return MeetingService(repository)


async def get_discussion_service(
    session: AsyncSession = Depends(get_db_session),
) -> DiscussionService:
    """
    Get a discussion service instance.

    Args:
        session: Database session

    Returns:
        Discussion service instance
    """
    repository = SQLALchemyMeetingRepository(session)
    return DiscussionService(repository)


async def get_communication_repository(
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a communication repository instance.

    Args:
        session: Database session

    Returns:
        Communication repository instance
    """

    return SQLAlchemyCommunicationRepository(session)


async def get_meeting_repository(
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a meeting repository instance.

    Args:
        session: Database session

    Returns:
        Meeting repository instance
    """

    return SQLALchemyMeetingRepository(session)


async def get_project_repository(
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a project repository instance.

    Args:
        session: Database session

    Returns:
        Project repository instance
    """
    from agent_comm_core.repositories import ProjectRepository

    return ProjectRepository(session)
