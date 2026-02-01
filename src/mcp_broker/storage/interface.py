"""
Abstract storage interface for MCP Broker Server.

This module defines the StorageBackend protocol that all storage
implementations must follow, enabling seamless switching between
in-memory and Redis backends.

The storage interface now supports project-scoped operations using
namespace prefixing pattern: "{project_id}:{resource_type}:{resource_id}"
"""

from typing import Protocol

from mcp_broker.models.message import Message
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.models.session import Session
from uuid import UUID


class StorageBackend(Protocol):
    """
    Abstract storage backend interface.

    This protocol defines the contract that all storage implementations
    must follow, providing methods for CRUD operations on protocols,
    sessions, and message queues.

    All methods are async to support non-blocking I/O operations.
    """

    async def get_protocol(
        self, name: str, version: str, project_id: str = "default"
    ) -> ProtocolDefinition | None:
        """Retrieve a protocol by name and version.

        Args:
            name: Protocol name
            version: Protocol version
            project_id: Project identifier (defaults to "default")

        Returns:
            ProtocolDefinition if found, None otherwise
        """
        ...

    async def save_protocol(
        self, protocol: ProtocolDefinition, project_id: str = "default"
    ) -> None:
        """Save a protocol definition.

        Args:
            protocol: Protocol definition to save
            project_id: Project identifier (defaults to "default")

        Raises:
            ValueError: If protocol with same name/version already exists
        """
        ...

    async def list_protocols(
        self,
        name: str | None = None,
        version: str | None = None,
        project_id: str = "default",
    ) -> list[ProtocolDefinition]:
        """List protocols with optional filtering.

        Args:
            name: Filter by protocol name (optional)
            version: Filter by version (optional)
            project_id: Project identifier (defaults to "default")

        Returns:
            List of matching protocols
        """
        ...

    async def delete_protocol(
        self, name: str, version: str, project_id: str = "default"
    ) -> bool:
        """Delete a protocol by name and version.

        Args:
            name: Protocol name
            version: Protocol version
            project_id: Project identifier (defaults to "default")

        Returns:
            True if deleted, False if not found
        """
        ...

    async def get_session(
        self, session_id: UUID, project_id: str = "default"
    ) -> Session | None:
        """Retrieve a session by ID.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            Session if found, None otherwise
        """
        ...

    async def save_session(
        self, session: Session, project_id: str = "default"
    ) -> None:
        """Save or update a session.

        Args:
            session: Session to save
            project_id: Project identifier (defaults to "default")
        """
        ...

    async def list_sessions(
        self, status: str | None = None, project_id: str = "default"
    ) -> list[Session]:
        """List sessions with optional status filter.

        Args:
            status: Filter by session status (optional)
            project_id: Project identifier (defaults to "default")

        Returns:
            List of matching sessions
        """
        ...

    async def delete_session(
        self, session_id: UUID, project_id: str = "default"
    ) -> bool:
        """Delete a session by ID.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            True if deleted, False if not found
        """
        ...

    async def enqueue_message(
        self, session_id: UUID, message: Message, project_id: str = "default"
    ) -> None:
        """Add a message to a session's queue.

        Args:
            session_id: Session UUID
            message: Message to enqueue
            project_id: Project identifier (defaults to "default")

        Raises:
            ValueError: If queue is at capacity
        """
        ...

    async def dequeue_messages(
        self, session_id: UUID, limit: int = 10, project_id: str = "default"
    ) -> list[Message]:
        """Dequeue messages for a session.

        Args:
            session_id: Session UUID
            limit: Maximum number of messages to dequeue
            project_id: Project identifier (defaults to "default")

        Returns:
            List of dequeued messages (oldest first)
        """
        ...

    async def get_queue_size(
        self, session_id: UUID, project_id: str = "default"
    ) -> int:
        """Get the current queue size for a session.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            Current queue size
        """
        ...

    async def clear_queue(
        self, session_id: UUID, project_id: str = "default"
    ) -> int:
        """Clear all messages from a session's queue.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            Number of messages cleared
        """
        ...
