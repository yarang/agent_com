"""
In-memory storage implementation for MCP Broker Server.

This module provides a simple in-memory storage backend suitable
for development and testing. Data is stored in dictionaries and
does not persist across server restarts.

The storage now supports project namespace isolation using the
pattern: "{project_id}:{resource_type}:{resource_id}"
"""

from collections import deque
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from mcp_broker.core.logging import get_logger
from mcp_broker.models.message import Message
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.models.session import Session
from mcp_broker.storage.interface import StorageBackend

logger = get_logger(__name__)


class InMemoryStorage(StorageBackend):
    """
    In-memory storage backend for development and testing.

    Storage structure with project namespace isolation:
    - protocols: Dict[(project_id, name, version), ProtocolDefinition]
    - sessions: Dict[(project_id, session_id), Session]
    - message_queues: Dict[(project_id, session_id), deque[Message]]
    - protocol_registry: Dict[(project_id, name), Set[version]] for fast lookup

    Attributes:
        queue_capacity: Maximum messages per session queue
    """

    def __init__(self, queue_capacity: int = 100) -> None:
        """Initialize in-memory storage.

        Args:
            queue_capacity: Maximum messages per session queue
        """
        self.queue_capacity = queue_capacity

        # Protocol storage with project namespace
        self._protocols: dict[tuple[str, str, str], ProtocolDefinition] = {}
        self._protocol_registry: dict[tuple[str, str], set[str]] = {}

        # Session storage with project namespace
        self._sessions: dict[tuple[str, UUID], Session] = {}

        # Message queues with project namespace
        self._message_queues: dict[tuple[str, UUID], deque[Message]] = {}

        logger.info(
            "InMemoryStorage initialized",
            extra={"context": {"queue_capacity": queue_capacity}},
        )

    def _protocol_key(self, project_id: str, name: str, version: str) -> tuple[str, str, str]:
        """Create a project-scoped key for protocol storage.

        Args:
            project_id: Project identifier
            name: Protocol name
            version: Protocol version

        Returns:
            Tuple key for protocol storage
        """
        return (project_id, name, version)

    def _protocol_registry_key(self, project_id: str, name: str) -> tuple[str, str]:
        """Create a project-scoped key for protocol registry.

        Args:
            project_id: Project identifier
            name: Protocol name

        Returns:
            Tuple key for protocol registry
        """
        return (project_id, name)

    def _session_key(self, project_id: str, session_id: UUID) -> tuple[str, UUID]:
        """Create a project-scoped key for session storage.

        Args:
            project_id: Project identifier
            session_id: Session UUID

        Returns:
            Tuple key for session storage
        """
        return (project_id, session_id)

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
        key = self._protocol_key(project_id, name, version)
        return self._protocols.get(key)

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
        key = self._protocol_key(project_id, protocol.name, protocol.version)

        if key in self._protocols:
            logger.warning(
                f"Protocol {protocol.name} v{protocol.version} already exists in project {project_id}",
                extra={
                    "context": {
                        "project_id": project_id,
                        "protocol_name": protocol.name,
                        "version": protocol.version,
                    }
                },
            )
            raise ValueError(
                f"Protocol '{protocol.name}' version '{protocol.version}' already exists in project '{project_id}'"
            )

        self._protocols[key] = protocol

        # Update registry for fast lookup
        registry_key = self._protocol_registry_key(project_id, protocol.name)
        if registry_key not in self._protocol_registry:
            self._protocol_registry[registry_key] = set()
        self._protocol_registry[registry_key].add(protocol.version)

        logger.info(
            f"Registered protocol: {protocol.name} v{protocol.version} in project {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "protocol_name": protocol.name,
                    "version": protocol.version,
                    "capabilities": protocol.capabilities,
                }
            },
        )

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
        # Filter by project first
        project_protocols = [
            p for (pid, _, _), p in self._protocols.items() if pid == project_id
        ]

        if name is None and version is None:
            return project_protocols

        if name is not None and version is not None:
            protocol = await self.get_protocol(name, version, project_id)
            return [protocol] if protocol else []

        if name is not None:
            registry_key = self._protocol_registry_key(project_id, name)
            versions = self._protocol_registry.get(registry_key, set())
            return [
                self._protocols[self._protocol_key(project_id, name, v)]
                for v in versions
                if self._protocol_key(project_id, name, v) in self._protocols
            ]

        # Filter by version only
        return [p for p in project_protocols if p.version == version]

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
        key = self._protocol_key(project_id, name, version)

        if key not in self._protocols:
            return False

        del self._protocols[key]

        # Update registry
        registry_key = self._protocol_registry_key(project_id, name)
        if registry_key in self._protocol_registry:
            self._protocol_registry[registry_key].discard(version)
            if not self._protocol_registry[registry_key]:
                del self._protocol_registry[registry_key]

        logger.info(
            f"Deleted protocol: {name} v{version} from project {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "protocol_name": name,
                    "version": version,
                }
            },
        )
        return True

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
        key = self._session_key(project_id, session_id)
        return self._sessions.get(key)

    async def save_session(
        self, session: Session, project_id: str = "default"
    ) -> None:
        """Save or update a session.

        Args:
            session: Session to save
            project_id: Project identifier (defaults to "default")
        """
        key = self._session_key(project_id, session.session_id)
        self._sessions[key] = session

        logger.debug(
            f"Saved session: {session.session_id} in project {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "session_id": str(session.session_id),
                    "status": session.status,
                }
            },
        )

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
        # Filter by project first
        project_sessions = [
            s for (pid, _), s in self._sessions.items() if pid == project_id
        ]

        if status:
            project_sessions = [s for s in project_sessions if s.status == status]

        return project_sessions

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
        key = self._session_key(project_id, session_id)

        if key not in self._sessions:
            return False

        # Clean up session data
        del self._sessions[key]

        queue_key = self._session_key(project_id, session_id)
        if queue_key in self._message_queues:
            del self._message_queues[queue_key]

        logger.info(
            f"Deleted session: {session_id} from project {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "session_id": str(session_id),
                }
            },
        )
        return True

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
        queue_key = self._session_key(project_id, session_id)

        if queue_key not in self._message_queues:
            self._message_queues[queue_key] = deque()

        queue = self._message_queues[queue_key]

        if len(queue) >= self.queue_capacity:
            logger.warning(
                f"Queue full for session {session_id} in project {project_id}",
                extra={
                    "context": {
                        "project_id": project_id,
                        "session_id": str(session_id),
                        "queue_size": len(queue),
                        "capacity": self.queue_capacity,
                    }
                },
            )
            raise ValueError(
                f"Message queue full ({self.queue_capacity} messages) "
                f"for session {session_id} in project {project_id}"
            )

        queue.append(message)

        # Update session queue size
        session = await self.get_session(session_id, project_id)
        if session:
            session.queue_size = len(queue)
            await self.save_session(session, project_id)

        logger.debug(
            f"Enqueued message for session {session_id} in project {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "session_id": str(session_id),
                    "queue_size": len(queue),
                }
            },
        )

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
        queue_key = self._session_key(project_id, session_id)

        if queue_key not in self._message_queues:
            return []

        queue = self._message_queues[queue_key]
        messages = []

        for _ in range(min(limit, len(queue))):
            if queue:
                messages.append(cast(Message, queue.popleft()))

        # Update session queue size
        session = await self.get_session(session_id, project_id)
        if session:
            session.queue_size = len(queue)
            await self.save_session(session, project_id)

        if messages:
            logger.debug(
                f"Dequeued {len(messages)} messages for session {session_id} in project {project_id}",
                extra={
                    "context": {
                        "project_id": project_id,
                        "session_id": str(session_id),
                        "count": len(messages),
                    }
                },
            )

        return messages

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
        queue_key = self._session_key(project_id, session_id)
        if queue_key not in self._message_queues:
            return 0
        return len(self._message_queues[queue_key])

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
        queue_key = self._session_key(project_id, session_id)

        if queue_key not in self._message_queues:
            return 0

        count = len(self._message_queues[queue_key])
        del self._message_queues[queue_key]

        # Update session queue size
        session = await self.get_session(session_id, project_id)
        if session:
            session.queue_size = 0
            await self.save_session(session, project_id)

        logger.info(
            f"Cleared {count} messages for session {session_id} in project {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "session_id": str(session_id),
                    "cleared": count,
                }
            },
        )
        return count
