"""
Repository layer for data access.

Provides abstract base classes and concrete implementations
for database operations using SQLAlchemy.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from agent_comm_core.models.communication import Communication, CommunicationCreate
from agent_comm_core.models.meeting import (
    Meeting,
    MeetingCreate,
    MeetingMessage,
    MeetingMessageCreate,
    MeetingParticipant,
    MeetingParticipantCreate,
)

# Import concrete repository implementations
from agent_comm_core.repositories.agent_api_key import AgentApiKeyRepository
from agent_comm_core.repositories.chat import ChatRepository
from agent_comm_core.repositories.project import ProjectRepository
from agent_comm_core.repositories.project_api_key import ProjectApiKeyRepository

# Import the new generic SQLAlchemy base
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase
from agent_comm_core.repositories.user import UserRepository

T = TypeVar("T")
CreateT = TypeVar("CreateT")


class BaseRepository(ABC, Generic[T, CreateT]):
    """
    Abstract base repository interface.

    Defines standard CRUD operations that all repositories must implement.
    """

    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None:
        """
        Retrieve an entity by its ID.

        Args:
            id: Unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def create(self, data: CreateT) -> T:
        """
        Create a new entity.

        Args:
            data: Entity creation data

        Returns:
            The created entity
        """
        pass

    @abstractmethod
    async def update(self, id: UUID, data: dict) -> T | None:
        """
        Update an existing entity.

        Args:
            id: Unique identifier of the entity
            data: Fields to update

        Returns:
            The updated entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """
        Delete an entity by its ID.

        Args:
            id: Unique identifier of the entity

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        List all entities with pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        pass


class CommunicationRepository(BaseRepository[Communication, CommunicationCreate]):
    """
    Repository for communication log operations.
    """

    @abstractmethod
    async def get_by_correlation_id(self, correlation_id: UUID) -> list[Communication]:
        """
        Retrieve all communications with a given correlation ID.

        Args:
            correlation_id: Correlation ID to filter by

        Returns:
            List of related communications
        """
        pass

    @abstractmethod
    async def get_by_agents(
        self,
        from_agent: str | None = None,
        to_agent: str | None = None,
        limit: int = 100,
    ) -> list[Communication]:
        """
        Retrieve communications filtered by agent IDs.

        Args:
            from_agent: Source agent filter (optional)
            to_agent: Target agent filter (optional)
            limit: Maximum number of results

        Returns:
            List of filtered communications
        """
        pass


class MeetingRepository(BaseRepository[Meeting, MeetingCreate]):
    """
    Repository for meeting operations.
    """

    @abstractmethod
    async def get_by_status(self, status: str) -> list[Meeting]:
        """
        Retrieve meetings by status.

        Args:
            status: Meeting status to filter by

        Returns:
            List of meetings with the given status
        """
        pass

    @abstractmethod
    async def add_participant(self, data: MeetingParticipantCreate) -> MeetingParticipant:
        """
        Add a participant to a meeting.

        Args:
            data: Participant creation data

        Returns:
            The created participant
        """
        pass

    @abstractmethod
    async def get_participants(self, meeting_id: UUID) -> list[MeetingParticipant]:
        """
        Get all participants for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of meeting participants
        """
        pass

    @abstractmethod
    async def record_message(self, data: MeetingMessageCreate) -> MeetingMessage:
        """
        Record a message in a meeting.

        Args:
            data: Message creation data

        Returns:
            The created message
        """
        pass

    @abstractmethod
    async def get_messages(self, meeting_id: UUID, limit: int = 100) -> list[MeetingMessage]:
        """
        Get messages from a meeting.

        Args:
            meeting_id: Meeting ID
            limit: Maximum number of messages

        Returns:
            List of meeting messages in sequence order
        """
        pass

    @abstractmethod
    async def update_status(self, meeting_id: UUID, status: str) -> Meeting | None:
        """
        Update the status of a meeting.

        Args:
            meeting_id: Meeting ID
            status: New status

        Returns:
            Updated meeting if found, None otherwise
        """
        pass


__all__ = [
    # Abstract base classes
    "BaseRepository",
    "CommunicationRepository",
    "MeetingRepository",
    # Generic base class (new)
    "SQLAlchemyRepositoryBase",
    # Concrete implementations
    "UserRepository",
    "AgentApiKeyRepository",
    "ProjectRepository",
    "ProjectApiKeyRepository",
    "ChatRepository",
]
