"""
Message Router for MCP Broker Server.

This module provides the MessageRouter class responsible for
routing messages between sessions using point-to-point and
broadcast patterns.

Supports project-scoped message routing with per-project
statistics tracking.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from mcp_broker.core.logging import get_logger
from mcp_broker.models.message import (
    BroadcastResult,
    DeliveryResult,
    Message,
)

if TYPE_CHECKING:
    from mcp_broker.session.manager import SessionManager
    from mcp_broker.storage.interface import StorageBackend


class MessageStatistics:
    """Message statistics for a project.

    Attributes:
        total_sent: Total messages sent
        total_delivered: Total messages successfully delivered
        total_queued: Total messages queued for offline sessions
        total_failed: Total messages that failed to deliver
        total_broadcast: Total broadcast messages sent
        last_activity: Timestamp of last message activity
    """

    def __init__(self) -> None:
        """Initialize message statistics."""
        self.total_sent: int = 0
        self.total_delivered: int = 0
        self.total_queued: int = 0
        self.total_failed: int = 0
        self.total_broadcast: int = 0
        self.last_activity: datetime | None = None

    def record_sent(self) -> None:
        """Record a message send attempt."""
        self.total_sent += 1
        self.last_activity = datetime.now(UTC)

    def record_delivered(self) -> None:
        """Record a successful message delivery."""
        self.total_delivered += 1
        self.last_activity = datetime.now(UTC)

    def record_queued(self) -> None:
        """Record a message queued for offline session."""
        self.total_queued += 1
        self.last_activity = datetime.now(UTC)

    def record_failed(self) -> None:
        """Record a failed message delivery."""
        self.total_failed += 1
        self.last_activity = datetime.now(UTC)

    def record_broadcast(self, recipient_count: int) -> None:
        """Record a broadcast message.

        Args:
            recipient_count: Number of recipients in broadcast
        """
        self.total_broadcast += 1
        self.total_sent += recipient_count
        self.last_activity = datetime.now(UTC)

    def to_dict(self) -> dict:
        """Convert statistics to dictionary.

        Returns:
            Dictionary representation of statistics
        """
        return {
            "total_sent": self.total_sent,
            "total_delivered": self.total_delivered,
            "total_queued": self.total_queued,
            "total_failed": self.total_failed,
            "total_broadcast": self.total_broadcast,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }


class MessageRouter:
    """
    Router for inter-session message delivery.

    The MessageRouter handles:
    - Point-to-point (1:1) message delivery
    - Broadcast (1:N) message delivery
    - Message queuing for offline recipients
    - Delivery confirmation and error handling
    - Per-project message statistics tracking

    Attributes:
        session_manager: Session manager for session access
        storage: Storage backend for persistence
        _statistics: Per-project message statistics
    """

    def __init__(
        self,
        session_manager: "SessionManager",
        storage: "StorageBackend",
    ) -> None:
        """Initialize the message router.

        Args:
            session_manager: Session manager for session access
            storage: Storage backend for persistence
        """
        self._session_manager = session_manager
        self._storage = storage
        self._dead_letter_queue: list[dict] = []
        self._statistics: dict[str, MessageStatistics] = {}

        logger = get_logger(__name__)
        logger.info("MessageRouter initialized")

    def _get_statistics(self, project_id: str) -> MessageStatistics:
        """Get or create statistics for a project.

        Args:
            project_id: Project identifier

        Returns:
            MessageStatistics for the project
        """
        if project_id not in self._statistics:
            self._statistics[project_id] = MessageStatistics()
        return self._statistics[project_id]

    def get_project_statistics(self, project_id: str) -> dict | None:
        """Get message statistics for a project.

        Args:
            project_id: Project identifier

        Returns:
            Dictionary of statistics or None if project not found
        """
        stats = self._statistics.get(project_id)
        return stats.to_dict() if stats else None

    def get_all_statistics(self) -> dict[str, dict]:
        """Get message statistics for all projects.

        Returns:
            Dictionary mapping project_id to statistics
        """
        return {project_id: stats.to_dict() for project_id, stats in self._statistics.items()}

    async def send_message(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        message: Message,
        project_id: str = "default",
    ) -> DeliveryResult:
        """Send a point-to-point message.

        Args:
            sender_id: Sender session UUID
            recipient_id: Recipient session UUID
            message: Message to send
            project_id: Project identifier for isolation (defaults to "default")

        Returns:
            DeliveryResult with delivery status
        """
        logger = get_logger(__name__)
        stats = self._get_statistics(project_id)
        stats.record_sent()

        # Verify sender exists and is in the same project
        sender = await self._session_manager.get_session(sender_id, project_id)
        if not sender:
            stats.record_failed()
            return DeliveryResult(
                success=False,
                error_reason=f"Sender session {sender_id} not found",
            )

        # Validate sender belongs to the project
        if sender.project_id != project_id:
            return DeliveryResult(
                success=False,
                error_reason=f"Sender session {sender_id} not in project '{project_id}'",
            )

        # Get recipient session (must be in same project)
        recipient = await self._session_manager.get_session(recipient_id, project_id)
        if not recipient:
            stats.record_failed()
            return DeliveryResult(
                success=False,
                error_reason=f"Recipient session {recipient_id} not found in project '{project_id}'",
            )

        # Verify recipient belongs to the same project
        if recipient.project_id != project_id:
            stats.record_failed()
            return DeliveryResult(
                success=False,
                error_reason=f"Cross-project messaging not allowed: {sender.project_id} -> {recipient.project_id}",
            )

        # Check compatibility
        common_protocols = sender.find_common_protocols(recipient)
        if message.protocol_name not in common_protocols:
            stats.record_failed()
            return DeliveryResult(
                success=False,
                error_reason=f"Protocol mismatch: no common version for '{message.protocol_name}'",
            )

        # If recipient is disconnected, queue the message
        if recipient.status == "disconnected":
            enqueue_result = await self._session_manager.enqueue_message(
                recipient_id, message, project_id
            )
            if enqueue_result.success:
                stats.record_queued()
                logger.info(
                    f"Message queued for offline session {recipient_id}",
                    extra={
                        "context": {
                            "message_id": str(message.message_id),
                            "sender_id": str(sender_id),
                            "recipient_id": str(recipient_id),
                            "project_id": project_id,
                        }
                    },
                )
                return DeliveryResult(
                    success=True,
                    queued=True,
                    queue_size=enqueue_result.queue_size,
                    message_id=message.message_id,
                )
            else:
                # Queue full - move to dead letter queue
                stats.record_failed()
                self._dead_letter_queue.append(
                    {
                        "message": message.model_dump(),
                        "failed_at": datetime.now(UTC).isoformat(),
                        "reason": "queue_full",
                        "sender_id": str(sender_id),
                        "recipient_id": str(recipient_id),
                        "project_id": project_id,
                    }
                )
                return DeliveryResult(
                    success=False,
                    error_reason="Queue full",
                    message_id=message.message_id,
                )

        # Recipient is active - deliver immediately
        # In production, would use SSE or WebSocket to push message
        # For now, we'll queue it for the session to retrieve
        enqueue_result = await self._session_manager.enqueue_message(
            recipient_id, message, project_id
        )

        if enqueue_result.success:
            stats.record_delivered()
            logger.info(
                f"Message delivered: {message.message_id} from {sender_id} to {recipient_id}",
                extra={
                    "context": {
                        "message_id": str(message.message_id),
                        "sender_id": str(sender_id),
                        "recipient_id": str(recipient_id),
                        "protocol": message.protocol_name,
                        "project_id": project_id,
                    }
                },
            )
            return DeliveryResult(
                success=True,
                delivered_at=datetime.now(UTC),
                message_id=message.message_id,
            )
        else:
            stats.record_failed()
            return DeliveryResult(
                success=False,
                error_reason=enqueue_result.error_reason,
                message_id=message.message_id,
            )

    async def broadcast_message(
        self,
        sender_id: UUID,
        message: Message,
        capability_filter: dict | None = None,
        project_id: str = "default",
    ) -> BroadcastResult:
        """Broadcast a message to all compatible sessions.

        Args:
            sender_id: Sender session UUID
            message: Message to broadcast (should have recipient_id=None)
            capability_filter: Optional filter for recipient capabilities
            project_id: Project identifier for isolation (defaults to "default")

        Returns:
            BroadcastResult with delivery summary
        """
        logger = get_logger(__name__)
        stats = self._get_statistics(project_id)

        # Get sender (must be in the project)
        sender = await self._session_manager.get_session(sender_id, project_id)
        if not sender:
            stats.record_failed()
            return BroadcastResult(
                success=False,
                reason=f"Sender session {sender_id} not found in project '{project_id}'",
            )

        # Validate sender belongs to the project
        if sender.project_id != project_id:
            return BroadcastResult(
                success=False,
                reason=f"Sender session {sender_id} not in project '{project_id}'",
            )

        # Get all active sessions in the project
        all_sessions = await self._session_manager.list_sessions(
            status_filter="active", project_id=project_id
        )

        # Filter out sender
        recipients = [s for s in all_sessions if s.session_id != sender_id]

        if not recipients:
            return BroadcastResult(
                success=True,
                delivery_count=0,
                reason="No other active sessions in project",
                recipients={"delivered": [], "failed": [], "skipped": [sender_id]},
            )

        # Apply capability filter if specified
        if capability_filter:
            filtered_recipients = []
            for session in recipients:
                # Check if session has required capabilities
                has_all = all(
                    feature in session.capabilities.supported_features
                    for feature in capability_filter.values()
                )
                if has_all:
                    filtered_recipients.append(session)
            recipients = filtered_recipients

        # Check protocol compatibility
        compatible_recipients = []
        for recipient in recipients:
            common_protocols = sender.find_common_protocols(recipient)
            if message.protocol_name in common_protocols:
                compatible_recipients.append(recipient)

        if not compatible_recipients:
            return BroadcastResult(
                success=True,
                delivery_count=0,
                reason="No compatible recipients",
                recipients={
                    "delivered": [],
                    "failed": [],
                    "skipped": [s.session_id for s in recipients] + [sender_id],
                },
            )

        # Broadcast to compatible recipients
        delivered: list[UUID] = []
        failed: list[UUID] = []
        skipped: list[UUID] = []

        for recipient in compatible_recipients:
            # Create individual message for this recipient
            recipient_message = Message(
                message_id=message.message_id,  # Same ID for broadcast
                sender_id=message.sender_id,
                recipient_id=recipient.session_id,
                timestamp=message.timestamp,
                protocol_name=message.protocol_name,
                protocol_version=message.protocol_version,
                payload=message.payload,
                headers=message.headers,
            )

            result = await self.send_message(
                sender_id, recipient.session_id, recipient_message, project_id
            )

            if result.success or result.queued:
                delivered.append(recipient.session_id)
            else:
                failed.append(recipient.session_id)

        # Include incompatible sessions in skipped
        incompatible = [
            s.session_id for s in recipients if s.session_id not in compatible_recipients
        ]
        skipped.extend(incompatible)
        skipped.append(sender_id)

        logger.info(
            f"Broadcast completed: {len(delivered)} delivered, {len(failed)} failed",
            extra={
                "context": {
                    "sender_id": str(sender_id),
                    "message_id": str(message.message_id),
                    "project_id": project_id,
                    "delivered": len(delivered),
                    "failed": len(failed),
                    "skipped": len(skipped),
                }
            },
        )

        # Record broadcast statistics
        stats.record_broadcast(len(delivered))

        return BroadcastResult(
            success=True,
            delivery_count=len(delivered),
            recipients={"delivered": delivered, "failed": failed, "skipped": skipped},
        )

    def get_dead_letter_queue(self) -> list[dict]:
        """Get messages in the dead-letter queue.

        Returns:
            List of failed message metadata
        """
        return self._dead_letter_queue.copy()

    def clear_dead_letter_queue(self) -> int:
        """Clear the dead-letter queue.

        Returns:
            Number of messages cleared
        """
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count
