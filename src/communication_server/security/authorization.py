"""
Role-Based Access Control (RBAC) decorators and utilities.

Provides permission decorators and authorization helpers for FastAPI endpoints.
"""

from collections.abc import Callable
from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, status

from agent_comm_core.db.models.user import UserRole
from agent_comm_core.models.auth import Agent, User
from communication_server.security.dependencies import get_current_agent, get_current_user

# ============================================================================
# Permission Constants
# ============================================================================


class Permission:
    """Permission constants for RBAC."""

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Project management
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_AGENTS = "project:manage_agents"

    # Agent API key management
    AGENT_KEY_CREATE = "agent_key:create"
    AGENT_KEY_READ = "agent_key:read"
    AGENT_KEY_REVOKE = "agent_key:revoke"

    # Communication
    COMMUNICATION_SEND = "communication:send"
    COMMUNICATION_READ = "communication:read"

    # Meetings
    MEETING_CREATE = "meeting:create"
    MEETING_READ = "meeting:read"
    MEETING_MANAGE = "meeting:manage"

    # Decisions
    DECISION_CREATE = "decision:create"
    DECISION_READ = "decision:read"
    DECISION_EXECUTE = "decision:execute"

    # Audit logs
    AUDIT_LOG_READ = "audit_log:read"

    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_PANIC = "system:panic"
    SYSTEM_STATUS = "system:status"


# ============================================================================
# Role-Permission Mapping
# ============================================================================


ROLE_PERMISSIONS = {
    UserRole.OWNER: [
        # Full permissions for their own projects
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_MANAGE_AGENTS,
        Permission.AGENT_KEY_CREATE,
        Permission.AGENT_KEY_READ,
        Permission.AGENT_KEY_REVOKE,
        Permission.COMMUNICATION_SEND,
        Permission.COMMUNICATION_READ,
        Permission.MEETING_CREATE,
        Permission.MEETING_READ,
        Permission.MEETING_MANAGE,
        Permission.DECISION_CREATE,
        Permission.DECISION_READ,
        Permission.DECISION_EXECUTE,
        Permission.AUDIT_LOG_READ,
    ],
    UserRole.ADMIN: [
        # Admin permissions except project deletion
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_MANAGE_AGENTS,
        Permission.AGENT_KEY_CREATE,
        Permission.AGENT_KEY_READ,
        Permission.AGENT_KEY_REVOKE,
        Permission.COMMUNICATION_SEND,
        Permission.COMMUNICATION_READ,
        Permission.MEETING_CREATE,
        Permission.MEETING_READ,
        Permission.MEETING_MANAGE,
        Permission.DECISION_CREATE,
        Permission.DECISION_READ,
        Permission.DECISION_EXECUTE,
        Permission.AUDIT_LOG_READ,
    ],
    UserRole.USER: [
        # Basic user permissions
        Permission.PROJECT_READ,
        Permission.COMMUNICATION_SEND,
        Permission.COMMUNICATION_READ,
        Permission.MEETING_READ,
        Permission.DECISION_READ,
    ],
    UserRole.READONLY: [
        # Read-only permissions
        Permission.PROJECT_READ,
        Permission.COMMUNICATION_READ,
        Permission.MEETING_READ,
        Permission.DECISION_READ,
    ],
}


# Agent capabilities mapping
AGENT_CAPABILITIES_PERMISSIONS = {
    "communicate": [Permission.COMMUNICATION_SEND, Permission.COMMUNICATION_READ],
    "create_meetings": [Permission.MEETING_CREATE],
    "propose_decisions": [Permission.DECISION_CREATE],
    "view_decisions": [Permission.DECISION_READ],
    "manage_decisions": [Permission.DECISION_EXECUTE],
    "project_chat": [Permission.COMMUNICATION_SEND, Permission.COMMUNICATION_READ],
}


# ============================================================================
# Permission Decorators
# ============================================================================


def require_permissions(*required_permissions: str) -> Callable:
    """Decorator to require specific permissions.

    Usage:
        @require_permissions(Permission.USER_CREATE)
        async def create_user(...):
            ...

    Args:
        *required_permissions: Required permission strings

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by FastAPI Depends)
            current_user: User = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check permissions
            if not has_permissions(current_user, *required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permissions}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(*roles: UserRole) -> Callable:
    """Decorator to require specific roles.

    Usage:
        @require_role(UserRole.ADMIN, UserRole.OWNER)
        async def admin_only_endpoint(...):
            ...

    Args:
        *roles: Required roles

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs
            current_user: User = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check role
            if current_user.role not in roles and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient privileges. Required roles: {roles}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_agent_capabilities(*capabilities: str) -> Callable:
    """Decorator to require specific agent capabilities.

    Usage:
        @require_agent_capabilities("communicate", "create_meetings")
        async def agent_endpoint(...):
            ...

    Args:
        *capabilities: Required capabilities

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get agent from kwargs
            current_agent: Agent = kwargs.get("current_agent")
            if not current_agent:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Agent authentication required",
                )

            # Check capabilities
            if not has_agent_capabilities(current_agent, *capabilities):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient capabilities. Required: {capabilities}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Permission Check Functions
# ============================================================================


def has_permissions(user: User, *required_permissions: str) -> bool:
    """Check if user has all required permissions.

    Args:
        user: User object
        *required_permissions: Required permission strings

    Returns:
        True if user has all permissions
    """
    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Get permissions for user's role
    role_perms = ROLE_PERMISSIONS.get(user.role, [])

    # Check custom permissions
    all_perms = set(role_perms) | set(user.permissions)

    # Check if all required permissions are present
    return all(perm in all_perms for perm in required_permissions)


def has_agent_capabilities(agent: Agent, *required_capabilities: str) -> bool:
    """Check if agent has all required capabilities.

    Args:
        agent: Agent object
        *required_capabilities: Required capability strings

    Returns:
        True if agent has all capabilities
    """
    # Check if agent is active
    if not agent.is_active:
        return False

    # Check if all required capabilities are present
    return all(cap in agent.capabilities for cap in required_capabilities)


def can_modify_project(user: User, project_owner_id: str, user_id: str) -> bool:
    """Check if user can modify a project.

    Args:
        user: User attempting to modify
        project_owner_id: ID of project owner
        user_id: ID of the user

    Returns:
        True if user can modify project
    """
    # Superusers can modify anything
    if user.is_superuser:
        return True

    # Owner can modify their own project
    if user_id == project_owner_id:
        return True

    # Admins can modify (if they're project owners)
    return user.role == UserRole.ADMIN


def can_access_project(user: User, project_owner_id: str) -> bool:
    """Check if user can access a project.

    Args:
        user: User attempting to access
        project_owner_id: ID of project owner

    Returns:
        True if user can access project
    """
    # Superusers can access everything
    if user.is_superuser:
        return True

    # Owner can access their project
    return user.id == project_owner_id


# ============================================================================
# FastAPI Dependencies
# ============================================================================


def require_permission(*required_permissions: str):
    """FastAPI dependency for permission checking.

    Usage:
        @router.get("/api/endpoint")
        async def endpoint(
            _: Annotated[None, Depends(require_permission(Permission.USER_READ))],
            current_user: Annotated[User, Depends(get_current_user)],
        ):
            ...

    Args:
        *required_permissions: Required permissions

    Returns:
        Dependency function
    """

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        """Check permissions."""
        if not has_permissions(current_user, *required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permissions}",
            )

    return dependency


def require_agent_capability(*required_capabilities: str):
    """FastAPI dependency for agent capability checking.

    Usage:
        @router.post("/api/endpoint")
        async def endpoint(
            _: Annotated[None, Depends(require_agent_capability("communicate"))],
            current_agent: Annotated[Agent, Depends(get_current_agent)],
        ):
            ...

    Args:
        *required_capabilities: Required capabilities

    Returns:
        Dependency function
    """

    async def dependency(current_agent: Annotated[Agent, Depends(get_current_agent)]) -> None:
        """Check capabilities."""
        if not has_agent_capabilities(current_agent, *required_capabilities):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient capabilities. Required: {required_capabilities}",
            )

    return dependency
