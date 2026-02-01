"""
Communication service for logging agent messages.
"""

from typing import Optional
from uuid import UUID

from agent_comm_core.models.communication import (
    Communication,
    CommunicationCreate,
    CommunicationDirection,
)
from agent_comm_core.repositories.base import CommunicationRepository


class CommunicationService:
    """
    Service for managing communication logs between agents.

    Provides methods for logging and retrieving agent communications
    with filtering and correlation capabilities.
    """

    def __init__(self, repository: CommunicationRepository) -> None:
        """
        Initialize the communication service.

        Args:
            repository: Communication repository instance
        """
        self._repository = repository

    async def log_communication(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: str,
        direction: CommunicationDirection = CommunicationDirection.INTERNAL,
        correlation_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> Communication:
        """
        Log a new communication between agents.

        Args:
            from_agent: Source agent identifier
            to_agent: Target agent identifier
            message_type: Type of message being sent
            content: Message content
            direction: Communication direction (default: INTERNAL)
            correlation_id: Optional correlation ID for related messages
            metadata: Optional additional metadata

        Returns:
            The created communication record

        Raises:
            ValueError: If required fields are invalid
        """
        create_data = CommunicationCreate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            direction=direction,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        return await self._repository.create(create_data)

    async def get_communication(self, id: UUID) -> Optional[Communication]:
        """
        Retrieve a communication by its ID.

        Args:
            id: Communication ID

        Returns:
            Communication if found, None otherwise
        """
        return await self._repository.get_by_id(id)

    async def get_communications(
        self,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None,
        correlation_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[Communication]:
        """
        Retrieve communications with optional filtering.

        Args:
            from_agent: Filter by source agent (optional)
            to_agent: Filter by target agent (optional)
            correlation_id: Filter by correlation ID (optional)
            limit: Maximum number of results

        Returns:
            List of matching communications
        """
        if correlation_id:
            return await self._repository.get_by_correlation_id(correlation_id)

        return await self._repository.get_by_agents(from_agent, to_agent, limit)

    async def list_recent(self, limit: int = 50) -> list[Communication]:
        """
        List recent communications.

        Args:
            limit: Maximum number of communications to return

        Returns:
            List of recent communications
        """
        return await self._repository.list_all(limit=limit)
