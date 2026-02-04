"""
Session Manager for MCP Broker Server.

This module provides the SessionManager class responsible for
managing client sessions, heartbeats, and message queues.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from mcp_broker.core.logging import get_logger
from mcp_broker.models.message import EnqueueResult, Message
from mcp_broker.models.session import (
    Session,
    SessionCapabilities,
    SessionStatus,
)

if TYPE_CHECKING:
    from mcp_broker.storage.interface import StorageBackend

logger = get_logger(__name__)


class SessionManager:
    """
    Manager for client session lifecycle.

    The SessionManager handles:
    - Session creation with unique ID assignment
    - Heartbeat monitoring and stale session detection
    - Message queuing for offline sessions
    - Session disconnection and cleanup
    - Duplicate session handling

    Attributes:
        storage: Storage backend for session persistence
        queue_capacity: Maximum messages per session queue
        stale_threshold: Seconds without heartbeat before marking stale
        disconnect_threshold: Seconds without heartbeat before disconnecting
    """

    def __init__(
        self,
        storage: "StorageBackend",
        queue_capacity: int = 100,
        stale_threshold: int = 30,
        disconnect_threshold: int = 60,
    ) -> None:
        """Initialize the session manager.

        Args:
            storage: Storage backend for persistence
            queue_capacity: Maximum messages per session queue
            stale_threshold: Seconds without heartbeat before stale
            disconnect_threshold: Seconds without heartbeat before disconnect
        """
        self._storage = storage
        self._queue_capacity = queue_capacity
        self._stale_threshold = stale_threshold
        self._disconnect_threshold = disconnect_threshold

        logger.info(
            "SessionManager initialized",
            extra={
                "context": {
                    "queue_capacity": queue_capacity,
                    "stale_threshold": stale_threshold,
                    "disconnect_threshold": disconnect_threshold,
                }
            },
        )

    async def create_session(
        self,
        capabilities: SessionCapabilities,
        session_id: UUID | None = None,
        project_id: str = "default",
    ) -> Session:
        """Create a new session.

        Args:
            capabilities: Session capabilities
            session_id: Optional specific session ID (for testing)
            project_id: Project identifier for isolation (default: "default")

        Returns:
            Created session with assigned UUID

        Raises:
            ValueError: If session_id already exists
        """
        # Use provided ID or generate new one
        sid = session_id or uuid4()

        # Check for duplicate
        existing = await self._storage.get_session(sid)
        if existing:
            # Duplicate session ID - terminate existing and create new
            logger.info(
                f"Duplicate session ID {sid}, terminating existing session",
                extra={"context": {"session_id": str(sid), "reason": "duplicate_registration"}},
            )
            await self.disconnect_session(sid)

        # Create new session with project association
        now = datetime.now(UTC)
        session = Session(
            session_id=sid,
            project_id=project_id,
            connection_time=now,
            last_heartbeat=now,
            status="active",
            capabilities=capabilities,
            queue_size=0,
        )

        await self._storage.save_session(session, session.project_id)

        logger.info(
            f"Session created: {sid}",
            extra={
                "context": {
                    "session_id": str(sid),
                    "project_id": project_id,
                    "capabilities": capabilities.model_dump(),
                }
            },
        )

        return session

    async def get_session(self, session_id: UUID, project_id: str = "default") -> Session | None:
        """Get a session by ID.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            Session if found, None otherwise
        """
        return await self._storage.get_session(session_id, project_id)

    async def update_heartbeat(
        self, session_id: UUID, project_id: str = "default"
    ) -> Session | None:
        """Update session heartbeat timestamp.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            Updated session if found, None otherwise
        """
        session = await self._storage.get_session(session_id, project_id)
        if not session:
            return None

        session.last_heartbeat = datetime.now(UTC)

        # Reset status to active if was stale
        if session.status == "stale":
            session.status = "active"
            logger.info(
                f"Session {session_id} recovered from stale",
                extra={"context": {"session_id": str(session_id), "project_id": project_id}},
            )

        await self._storage.save_session(session, session.project_id)

        logger.debug(
            f"Heartbeat updated for session {session_id}",
            extra={"context": {"session_id": str(session_id), "project_id": project_id}},
        )

        return session

    async def list_sessions(
        self,
        status_filter: SessionStatus | None = None,
        project_id: str = "default",
    ) -> list[Session]:
        """List sessions with optional status filter.

        Args:
            status_filter: Filter by session status (optional)
            project_id: Project identifier (defaults to "default")

        Returns:
            List of matching sessions
        """
        sessions = await self._storage.list_sessions(status=status_filter, project_id=project_id)

        logger.debug(
            f"Listed sessions: status={status_filter}, project={project_id}, count={len(sessions)}",
            extra={
                "context": {
                    "status_filter": status_filter,
                    "project_id": project_id,
                    "count": len(sessions),
                }
            },
        )

        return sessions

    async def disconnect_session(self, session_id: UUID, project_id: str = "default") -> bool:
        """Disconnect a session.

        Args:
            session_id: Session UUID
            project_id: Project identifier (defaults to "default")

        Returns:
            True if session was disconnected, False if not found
        """
        session = await self._storage.get_session(session_id, project_id)
        if not session:
            return False

        # Mark as disconnected
        session.status = "disconnected"
        await self._storage.save_session(session, session.project_id)

        # Note: Keep session in storage to allow message queuing for offline sessions
        # Session will be fully cleaned up by cleanup_expired_sessions after threshold

        logger.info(
            f"Session disconnected: {session_id}",
            extra={"context": {"session_id": str(session_id), "project_id": project_id}},
        )

        return True

    async def enqueue_message(
        self,
        recipient_id: UUID,
        message: Message,
        project_id: str = "default",
    ) -> EnqueueResult:
        """Enqueue a message for a session.

        Args:
            recipient_id: Target session UUID
            message: Message to enqueue
            project_id: Project identifier (defaults to "default")

        Returns:
            EnqueueResult with operation status
        """
        # Check if session exists
        session = await self._storage.get_session(recipient_id, project_id)
        if not session:
            return EnqueueResult(
                success=False,
                queue_size=0,
                error_reason=f"Session {recipient_id} not found",
            )

        # Check queue capacity
        current_size = await self._storage.get_queue_size(recipient_id, project_id)
        if current_size >= self._queue_capacity:
            logger.warning(
                f"Queue full for session {recipient_id}",
                extra={
                    "context": {
                        "session_id": str(recipient_id),
                        "project_id": project_id,
                        "queue_size": current_size,
                        "capacity": self._queue_capacity,
                    }
                },
            )
            return EnqueueResult(
                success=False,
                queue_size=current_size,
                error_reason="Queue full",
            )

        # Check for warning threshold
        warning_threshold = int(self._queue_capacity * 0.9)
        if current_size >= warning_threshold:
            logger.warning(
                f"Queue near capacity for session {recipient_id}",
                extra={
                    "context": {
                        "session_id": str(recipient_id),
                        "project_id": project_id,
                        "queue_size": current_size,
                        "capacity": self._queue_capacity,
                        "usage_percent": int(current_size / self._queue_capacity * 100),
                    }
                },
            )

        # Enqueue message
        try:
            await self._storage.enqueue_message(recipient_id, message, project_id)
            new_size = current_size + 1

            return EnqueueResult(success=True, queue_size=new_size)
        except ValueError as e:
            return EnqueueResult(
                success=False,
                queue_size=current_size,
                error_reason=str(e),
            )

    async def dequeue_messages(
        self,
        session_id: UUID,
        limit: int = 10,
        project_id: str = "default",
    ) -> list[Message]:
        """Dequeue messages for a session.

        Args:
            session_id: Session UUID
            limit: Maximum messages to dequeue
            project_id: Project identifier (defaults to "default")

        Returns:
            List of dequeued messages (oldest first)
        """
        messages = await self._storage.dequeue_messages(session_id, limit, project_id)

        if messages:
            logger.debug(
                f"Dequeued {len(messages)} messages for session {session_id}",
                extra={
                    "context": {
                        "session_id": str(session_id),
                        "project_id": project_id,
                        "count": len(messages),
                    }
                },
            )

        return messages

    async def check_stale_sessions(self, project_id: str | None = None) -> list[Session]:
        """Check for stale sessions and update their status.

        Args:
            project_id: Optional project ID to scope check (None = "default" for backward compatibility)

        Returns:
            List of sessions that became stale
        """
        # Use "default" project if None specified (for backward compatibility)
        scoped_project_id = project_id if project_id is not None else "default"
        all_sessions = await self._storage.list_sessions(project_id=scoped_project_id)
        stale_sessions: list[Session] = []

        for session in all_sessions:
            if session.status == "active" and session.is_stale(self._stale_threshold):
                session.status = "stale"
                await self._storage.save_session(session, session.project_id)
                stale_sessions.append(session)

                logger.info(
                    f"Session marked as stale: {session.session_id}",
                    extra={
                        "context": {
                            "session_id": str(session.session_id),
                            "project_id": session.project_id,
                            "last_heartbeat": session.last_heartbeat.isoformat(),
                        }
                    },
                )

        return stale_sessions

    async def cleanup_expired_sessions(self, project_id: str | None = None) -> list[Session]:
        """Disconnect sessions that have exceeded disconnect threshold.

        Args:
            project_id: Optional project ID to scope cleanup (None = "default" for backward compatibility)

        Returns:
            List of sessions that were disconnected
        """
        # Use "default" project if None specified (for backward compatibility)
        scoped_project_id = project_id if project_id is not None else "default"
        all_sessions = await self._storage.list_sessions(project_id=scoped_project_id)
        disconnected: list[Session] = []

        for session in all_sessions:
            if session.status in ("active", "stale") and session.should_disconnect(
                self._disconnect_threshold
            ):
                await self.disconnect_session(session.session_id, session.project_id)
                disconnected.append(session)

                logger.info(
                    f"Session disconnected due to timeout: {session.session_id}",
                    extra={
                        "context": {
                            "session_id": str(session.session_id),
                            "project_id": session.project_id,
                            "status": session.status,
                        }
                    },
                )

        return disconnected
