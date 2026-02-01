"""
Cross-Project Message Router for MCP Broker Server.

This module provides the CrossProjectRouter class responsible for
handling authorized inter-project communication between sessions
from different projects.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from mcp_broker.core.logging import get_logger
from mcp_broker.models.message import DeliveryResult, Message
from mcp_broker.models.project import CrossProjectPermission, ProjectDefinition
from mcp_broker.models.session import Session

if TYPE_CHECKING:
    from mcp_broker.project.registry import ProjectRegistry
    from mcp_broker.session.manager import SessionManager


class CrossProjectRouter:
    """
    Router for authorized inter-project message delivery.

    The CrossProjectRouter handles:
    - Cross-project permission validation
    - Protocol compatibility checking between projects
    - Rate limiting for cross-project communication
    - Message transformation between protocol versions
    - Audit logging for cross-project operations

    Attributes:
        project_registry: Project registry for permission checks
        session_manager: Session manager for session access
    """

    def __init__(
        self,
        project_registry: "ProjectRegistry",
        session_manager: "SessionManager",
    ) -> None:
        """Initialize the cross-project router.

        Args:
            project_registry: Project registry for permission checks
            session_manager: Session manager for session access
        """
        self._project_registry = project_registry
        self._session_manager = session_manager

        # Track message counts for rate limiting
        self._message_counts: dict[tuple[str, str], list[datetime]] = {}

        logger = get_logger(__name__)
        logger.info("CrossProjectRouter initialized")

    async def send_cross_project_message(
        self,
        sender_id: UUID,
        sender_project_id: str,
        recipient_id: UUID,
        recipient_project_id: str,
        message: Message,
    ) -> DeliveryResult:
        """Send a message across project boundaries.

        Args:
            sender_id: Sender session UUID
            sender_project_id: Sender project identifier
            recipient_id: Recipient session UUID
            recipient_project_id: Recipient project identifier
            message: Message to send

        Returns:
            DeliveryResult with delivery status
        """
        logger = get_logger(__name__)

        # Validate both projects exist
        sender_project = await self._project_registry.get_project(sender_project_id)
        if not sender_project:
            return DeliveryResult(
                success=False,
                error_reason=f"Sender project '{sender_project_id}' not found",
            )

        recipient_project = await self._project_registry.get_project(recipient_project_id)
        if not recipient_project:
            return DeliveryResult(
                success=False,
                error_reason=f"Recipient project '{recipient_project_id}' not found",
            )

        # Check if cross-project communication is allowed
        permission = self._check_cross_project_permission(
            sender_project, recipient_project, message.protocol_name
        )
        if not permission:
            logger.warning(
                f"Cross-project communication not allowed: {sender_project_id} -> {recipient_project_id}",
                extra={
                    "context": {
                        "sender_project": sender_project_id,
                        "recipient_project": recipient_project_id,
                        "protocol": message.protocol_name,
                    }
                },
            )
            return DeliveryResult(
                success=False,
                error_reason=f"Cross-project communication not authorized for protocol '{message.protocol_name}'",
            )

        # Check rate limits
        rate_limit = permission.message_rate_limit
        if rate_limit > 0:
            if not self._check_rate_limit(sender_project_id, recipient_project_id, rate_limit):
                return DeliveryResult(
                    success=False,
                    error_reason=f"Rate limit exceeded for {sender_project_id} -> {recipient_project_id}",
                )

        # Get sender and recipient sessions
        sender = await self._session_manager.get_session(sender_id, sender_project_id)
        if not sender:
            return DeliveryResult(
                success=False,
                error_reason=f"Sender session {sender_id} not found",
            )

        recipient = await self._session_manager.get_session(recipient_id, recipient_project_id)
        if not recipient:
            return DeliveryResult(
                success=False,
                error_reason=f"Recipient session {recipient_id} not found",
            )

        # Check protocol compatibility between projects
        if not self._check_protocol_compatibility(
            sender, recipient, message.protocol_name
        ):
            return DeliveryResult(
                success=False,
                error_reason=f"Protocol '{message.protocol_name}' not compatible between projects",
            )

        # Deliver message (using recipient's project context)
        from mcp_broker.routing.router import MessageRouter

        # Note: We need to import MessageRouter dynamically to avoid circular dependency
        # In production, would inject this as a dependency

        # For now, deliver through the session manager's enqueue mechanism
        try:
            if recipient.status == "disconnected":
                enqueue_result = await self._session_manager.enqueue_message(
                    recipient_id, message, recipient_project_id
                )
                if enqueue_result.success:
                    logger.info(
                        f"Cross-project message queued: {sender_project_id} -> {recipient_project_id}",
                        extra={
                            "context": {
                                "message_id": str(message.message_id),
                                "sender_id": str(sender_id),
                                "recipient_id": str(recipient_id),
                                "sender_project": sender_project_id,
                                "recipient_project": recipient_project_id,
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
                    return DeliveryResult(
                        success=False,
                        error_reason=enqueue_result.error_reason,
                        message_id=message.message_id,
                    )
            else:
                # Active recipient - queue for delivery
                enqueue_result = await self._session_manager.enqueue_message(
                    recipient_id, message, recipient_project_id
                )

                if enqueue_result.success:
                    logger.info(
                        f"Cross-project message delivered: {sender_project_id} -> {recipient_project_id}",
                        extra={
                            "context": {
                                "message_id": str(message.message_id),
                                "sender_id": str(sender_id),
                                "recipient_id": str(recipient_id),
                                "sender_project": sender_project_id,
                                "recipient_project": recipient_project_id,
                                "protocol": message.protocol_name,
                            }
                        },
                    )
                    return DeliveryResult(
                        success=True,
                        delivered_at=datetime.now(UTC),
                        message_id=message.message_id,
                    )
                else:
                    return DeliveryResult(
                        success=False,
                        error_reason=enqueue_result.error_reason,
                        message_id=message.message_id,
                    )

        except Exception as e:
            logger.error(
                f"Cross-project delivery error: {e}",
                extra={
                    "context": {
                        "sender_project": sender_project_id,
                        "recipient_project": recipient_project_id,
                        "error": str(e),
                    }
                },
            )
            return DeliveryResult(
                success=False,
                error_reason=f"Delivery failed: {e}",
                message_id=message.message_id,
            )

    def _check_cross_project_permission(
        self,
        sender_project: ProjectDefinition,
        recipient_project: ProjectDefinition,
        protocol_name: str,
    ) -> CrossProjectPermission | None:
        """Check if cross-project communication is allowed.

        Args:
            sender_project: Sender project definition
            recipient_project: Recipient project definition
            protocol_name: Protocol to check

        Returns:
            CrossProjectPermission if allowed, None otherwise
        """
        # Both projects must explicitly allow cross-project communication
        if not sender_project.config.allow_cross_project:
            return None

        if not recipient_project.config.allow_cross_project:
            return None

        # Check if sender has permission for recipient project
        for perm in sender_project.cross_project_permissions:
            if perm.target_project_id == recipient_project.project_id:
                # Check if protocol is in whitelist
                if not perm.allowed_protocols or protocol_name in perm.allowed_protocols:
                    return perm

        # Check if recipient has permission for sender project
        for perm in recipient_project.cross_project_permissions:
            if perm.target_project_id == sender_project.project_id:
                # Check if protocol is in whitelist
                if not perm.allowed_protocols or protocol_name in perm.allowed_protocols:
                    return perm

        # If both projects have allow_cross_project=True but no specific permissions,
        # allow communication (implicit permission)
        if sender_project.config.allow_cross_project and recipient_project.config.allow_cross_project:
            # Create implicit permission
            return CrossProjectPermission(
                target_project_id=recipient_project.project_id,
                allowed_protocols=[],
                message_rate_limit=0,  # No limit
            )

        return None

    def _check_rate_limit(
        self,
        sender_project: str,
        recipient_project: str,
        rate_limit: int,
    ) -> bool:
        """Check if rate limit allows sending message.

        Args:
            sender_project: Sender project ID
            recipient_project: Recipient project ID
            rate_limit: Messages per minute limit (0 = unlimited)

        Returns:
            True if within rate limit, False otherwise
        """
        if rate_limit == 0:
            return True

        key = (sender_project, recipient_project)
        now = datetime.now(UTC)
        one_minute_ago = now.replace(second=now.second - 60)

        # Clean old entries
        if key in self._message_counts:
            self._message_counts[key] = [
                ts for ts in self._message_counts[key] if ts > one_minute_ago
            ]

        # Check current count
        current_count = len(self._message_counts.get(key, []))
        if current_count >= rate_limit:
            return False

        # Record this message
        if key not in self._message_counts:
            self._message_counts[key] = []
        self._message_counts[key].append(now)

        return True

    def _check_protocol_compatibility(
        self, sender: Session, recipient: Session, protocol_name: str
    ) -> bool:
        """Check if protocol is compatible between sessions.

        Args:
            sender: Sender session
            recipient: Recipient session
            protocol_name: Protocol name to check

        Returns:
            True if compatible, False otherwise
        """
        # Check if both sessions support the protocol
        sender_versions = sender.capabilities.supported_protocols.get(protocol_name, [])
        recipient_versions = recipient.capabilities.supported_protocols.get(protocol_name, [])

        if not sender_versions or not recipient_versions:
            return False

        # Find common version
        common_versions = set(sender_versions) & set(recipient_versions)
        return len(common_versions) > 0

    def get_cross_project_stats(self) -> dict[str, int]:
        """Get statistics for cross-project communication.

        Returns:
            Dictionary with statistics
        """
        total_pairs = len(self._message_counts)
        total_messages = sum(len(timestamps) for timestamps in self._message_counts.values())

        return {
            "active_project_pairs": total_pairs,
            "total_messages_sent": total_messages,
        }
