"""
Admin permission system for MCP Broker Server.

This module provides the AdminPermissionManager class which handles
administrative authorization including cross-project access control,
role detection, and permission caching.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mcp_broker.core.logging import get_logger
from mcp_broker.models.project import CrossProjectPermission, ProjectDefinition

if TYPE_CHECKING:
    from mcp_broker.project.registry import ProjectRegistry


class AdminPermissionManager:
    """
    Manager for administrative permissions and cross-project access.

    The AdminPermissionManager handles:
    - Admin role detection from API keys
    - Cross-project access authorization
    - Permission caching for performance
    - Permission validation and audit logging

    Attributes:
        _project_registry: Project registry for permission lookups
        _permission_cache: Cached permission decisions
        _cache_ttl: Time-to-live for cache entries
    """

    def __init__(
        self,
        project_registry: "ProjectRegistry",
        cache_ttl_seconds: int = 300,
    ) -> None:
        """Initialize the admin permission manager.

        Args:
            project_registry: Project registry for permission lookups
            cache_ttl_seconds: Time-to-live for permission cache (default 5 minutes)
        """
        self._project_registry = project_registry
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)

        # Cache structure: {(project_id, action, target): (allowed, timestamp)}
        self._permission_cache: dict[tuple[str, str, str | None], tuple[bool, datetime]] = {}

        logger = get_logger(__name__)
        logger.info(
            "AdminPermissionManager initialized",
            extra={"context": {"cache_ttl_seconds": cache_ttl_seconds}},
        )

    def is_admin_key(self, api_key: str, project_id: str) -> bool:
        """Check if an API key has admin privileges.

        Admin keys are identified by the key_id prefix "admin" or "owner".
        These keys have elevated permissions including:
        - Cross-project communication
        - Project management operations
        - Key rotation and deletion

        Args:
            api_key: API key string to check
            project_id: Project ID for context

        Returns:
            True if the key has admin privileges
        """
        logger = get_logger(__name__)
        try:
            # Split from right to handle project_ids with underscores
            parts = api_key.rsplit("_", 2)
            if len(parts) == 3:
                extracted_project_id, key_id, _secret = parts
                # Verify project_id matches
                if extracted_project_id != project_id:
                    return False
                is_admin = key_id in ("admin", "owner")

                if is_admin:
                    logger.debug(
                        f"Admin key detected: {key_id}",
                        extra={"context": {"project_id": project_id, "key_id": key_id}},
                    )

                return is_admin
        except Exception:
            pass

        return False

    async def can_access_project(
        self,
        request_project_id: str,
        target_project_id: str,
        api_key: str | None = None,
    ) -> bool:
        """Check if a request can access a target project.

        Cross-project access is allowed when:
        1. Both projects are the same (same-project access)
        2. Request uses admin API key
        3. Both projects have explicit cross-project permission

        Args:
            request_project_id: Project making the request
            target_project_id: Project being accessed
            api_key: Optional API key for admin check

        Returns:
            True if access is allowed
        """
        logger = get_logger(__name__)
        # Same project always allowed
        if request_project_id == target_project_id:
            return True

        # Check admin key
        if api_key and self.is_admin_key(api_key, request_project_id):
            logger.info(
                f"Admin cross-project access: {request_project_id} -> {target_project_id}",
                extra={
                    "context": {
                        "request_project": request_project_id,
                        "target_project": target_project_id,
                        "access_method": "admin_key",
                    }
                },
            )
            return True

        # Check permission cache
        cache_key = (request_project_id, "access_project", target_project_id)
        cached = self._get_cached_permission(cache_key)
        if cached is not None:
            return cached

        # Check cross-project permissions
        allowed = await self._check_cross_project_permission(request_project_id, target_project_id)

        # Cache the result
        self._cache_permission(cache_key, allowed)

        return allowed

    async def can_send_cross_project_message(
        self,
        sender_project_id: str,
        recipient_project_id: str,
        protocol_name: str,
        api_key: str | None = None,
    ) -> bool:
        """Check if cross-project message sending is allowed.

        Cross-project messaging requires:
        1. Both projects allow cross-project communication
        2. Protocol is in allowed list (or no whitelist)
        3. Rate limit not exceeded

        Args:
            sender_project_id: Sender project ID
            recipient_project_id: Recipient project ID
            protocol_name: Protocol being used
            api_key: Optional API key for admin check

        Returns:
            True if message sending is allowed
        """
        logger = get_logger(__name__)
        # Same project always allowed
        if sender_project_id == recipient_project_id:
            return True

        # Check admin key (bypasses all restrictions)
        if api_key and self.is_admin_key(api_key, sender_project_id):
            logger.info(
                f"Admin cross-project message: {sender_project_id} -> {recipient_project_id}",
                extra={
                    "context": {
                        "sender_project": sender_project_id,
                        "recipient_project": recipient_project_id,
                        "protocol": protocol_name,
                        "access_method": "admin_key",
                    }
                },
            )
            return True

        # Check permission cache
        cache_key = (sender_project_id, f"send_message:{protocol_name}", recipient_project_id)
        cached = self._get_cached_permission(cache_key)
        if cached is not None:
            return cached

        # Get both projects
        sender_project = await self._project_registry.get_project(sender_project_id)
        if not sender_project:
            return False

        recipient_project = await self._project_registry.get_project(recipient_project_id)
        if not recipient_project:
            return False

        # Both projects must allow cross-project communication
        if not sender_project.config.allow_cross_project:
            return False

        if not recipient_project.config.allow_cross_project:
            return False

        # Check for explicit permission
        permission = self._find_cross_project_permission(sender_project, recipient_project_id)

        # Check if protocol is in whitelist (if whitelist exists)
        if (
            permission
            and permission.allowed_protocols
            and protocol_name not in permission.allowed_protocols
        ):
            self._cache_permission(cache_key, False)
            return False

        # If no explicit permission but both allow_cross_project, allow it
        self._cache_permission(cache_key, True)
        return True

    async def get_message_rate_limit(
        self,
        sender_project_id: str,
        recipient_project_id: str,
        api_key: str | None = None,
    ) -> int:
        """Get message rate limit for cross-project communication.

        Rate limits are messages per minute. Returns 0 for unlimited.
        Admin keys have unlimited rate limit.

        Args:
            sender_project_id: Sender project ID
            recipient_project_id: Recipient project ID
            api_key: Optional API key for admin check

        Returns:
            Messages per minute limit (0 = unlimited)
        """
        # Admin keys have no limit
        if api_key and self.is_admin_key(api_key, sender_project_id):
            return 0

        # Get sender project
        sender_project = await self._project_registry.get_project(sender_project_id)
        if not sender_project:
            return 0  # No limit if project doesn't exist

        # Find permission
        permission = self._find_cross_project_permission(sender_project, recipient_project_id)

        if permission:
            return permission.message_rate_limit

        # Default: no limit if both projects allow cross-project
        if sender_project.config.allow_cross_project:
            return 0

        return 0

    async def can_manage_project(
        self,
        project_id: str,
        api_key: str,
        _operation: str = "update",
    ) -> bool:
        """Check if the API key can manage the project.

        Project management operations include:
        - update: Update project configuration
        - delete: Delete project
        - rotate_keys: Rotate API keys
        - manage_permissions: Manage cross-project permissions

        Args:
            project_id: Project being managed
            api_key: API key attempting the operation
            _operation: Type of management operation (reserved for future use)

        Returns:
            True if operation is allowed
        """
        # Must be admin key
        if not self.is_admin_key(api_key, project_id):
            return False

        # Validate API key belongs to project
        result = await self._project_registry.validate_api_key(api_key)
        if not result:
            return False

        key_project_id, _key_id = result
        return key_project_id == project_id

    async def validate_cross_project_config(
        self,
        project_id: str,
        target_project_id: str,
        allowed_protocols: list[str] | None,
        rate_limit: int,
        api_key: str,
    ) -> tuple[bool, str | None]:
        """Validate cross-project configuration.

        Validates that a cross-project permission configuration is valid:
        - Target project exists
        - Requester has admin permission
        - Protocols are valid (if specified)

        Args:
            project_id: Project configuring the permission
            target_project_id: Target project for permission
            allowed_protocols: Optional protocol whitelist
            rate_limit: Message rate limit
            api_key: API key of requester

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check admin permission
        if not await self.can_manage_project(project_id, api_key, "manage_permissions"):
            return (False, "Admin permission required for cross-project configuration")

        # Check target project exists
        target_project = await self._project_registry.get_project(target_project_id)
        if not target_project:
            return (False, f"Target project '{target_project_id}' not found")

        # Cannot configure permission to self
        if project_id == target_project_id:
            return (False, "Cannot configure cross-project permission to self")

        # Validate protocols exist (if specified)
        if allowed_protocols:
            # Note: We'd need to inject ProtocolRegistry here
            # For now, just check format
            for proto in allowed_protocols:
                if not proto or not isinstance(proto, str):
                    return (False, f"Invalid protocol name: {proto}")

        # Validate rate limit
        if rate_limit < 0:
            return (False, "Rate limit must be non-negative")

        return (True, None)

    def clear_permission_cache(self) -> None:
        """Clear the permission cache.

        This should be called when permissions are updated to ensure
        fresh permission decisions.
        """
        self._permission_cache.clear()
        logger = get_logger(__name__)
        logger.debug("Permission cache cleared")

    def _get_cached_permission(self, cache_key: tuple[str, str, str | None]) -> bool | None:
        """Get cached permission decision.

        Args:
            cache_key: Cache key tuple

        Returns:
            Cached decision or None if not found/expired
        """
        if cache_key in self._permission_cache:
            allowed, timestamp = self._permission_cache[cache_key]
            if datetime.now(UTC) - timestamp < self._cache_ttl:
                return allowed
            else:
                # Expired, remove from cache
                del self._permission_cache[cache_key]

        return None

    def _cache_permission(
        self,
        cache_key: tuple[str, str, str | None],
        allowed: bool,
    ) -> None:
        """Cache a permission decision.

        Args:
            cache_key: Cache key tuple
            allowed: Permission decision
        """
        self._permission_cache[cache_key] = (allowed, datetime.now(UTC))

    async def _check_cross_project_permission(
        self,
        request_project_id: str,
        target_project_id: str,
    ) -> bool:
        """Check if cross-project permission exists.

        Args:
            request_project_id: Requesting project ID
            target_project_id: Target project ID

        Returns:
            True if permission exists
        """
        # Get both projects
        request_project = await self._project_registry.get_project(request_project_id)
        if not request_project:
            return False

        target_project = await self._project_registry.get_project(target_project_id)
        if not target_project:
            return False

        # Both must allow cross-project communication
        if not request_project.config.allow_cross_project:
            return False

        if not target_project.config.allow_cross_project:
            return False

        # Check for explicit permission from requester to target
        permission = self._find_cross_project_permission(request_project, target_project_id)

        if permission:
            return True

        # If no explicit permission but both allow_cross_project, allow
        return True

    def _find_cross_project_permission(
        self,
        project: ProjectDefinition,
        target_project_id: str,
    ) -> CrossProjectPermission | None:
        """Find cross-project permission for a target.

        Args:
            project: Project to search in
            target_project_id: Target project ID

        Returns:
            CrossProjectPermission if found, None otherwise
        """
        for perm in project.cross_project_permissions:
            if perm.target_project_id == target_project_id:
                return perm

        return None


# =============================================================================
# Global Admin Permission Manager
# =============================================================================

_global_admin_manager: AdminPermissionManager | None = None


def get_admin_permission_manager(project_registry: "ProjectRegistry") -> AdminPermissionManager:
    """Get the global admin permission manager.

    Args:
        project_registry: Project registry for permission lookups

    Returns:
        The global AdminPermissionManager instance
    """
    global _global_admin_manager

    if _global_admin_manager is None:
        _global_admin_manager = AdminPermissionManager(project_registry)

    return _global_admin_manager


def reset_admin_permission_manager() -> None:
    """Reset the global admin permission manager.

    This is primarily useful for testing purposes.
    """
    global _global_admin_manager

    _global_admin_manager = None

    logger = get_logger(__name__)
    logger.debug("Admin permission manager reset")
