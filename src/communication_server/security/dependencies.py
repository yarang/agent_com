"""
FastAPI dependencies for authentication.

Provides dependency injection functions for protected routes that
require JWT or API token authentication.
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_comm_core.models.auth import Agent, User

from communication_server.security.auth import AuthService, get_auth_service
from communication_server.security.tokens import extract_token_from_header


# OAuth2 scheme for JWT tokens (used by Swagger UI)
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> User:
    """
    Get the current authenticated dashboard user from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    auth_service = get_auth_service()

    user = await auth_service.authenticate_user_with_token(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    Args:
        current_user: Authenticated user from get_current_user

    Returns:
        Active User object

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current admin user.

    Args:
        current_user: Authenticated user from get_current_user

    Returns:
        Admin User object

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def get_current_agent(
    authorization: str = Header(...),
) -> Agent:
    """
    Get the current authenticated agent from API token.

    Args:
        authorization: Authorization header value

    Returns:
        Authenticated Agent object

    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = extract_token_from_header(authorization)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = get_auth_service()
    agent = await auth_service.authenticate_agent(token)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent account is disabled",
        )

    return agent


async def require_agent(
    agent: Agent = Depends(get_current_agent),
) -> Agent:
    """
    Require agent authentication (alias for get_current_agent).

    This is a semantic alias to make route definitions clearer.

    Args:
        agent: Authenticated agent from get_current_agent

    Returns:
        Authenticated Agent object
    """
    return agent


async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Use this dependency for endpoints that work for both authenticated
    and anonymous users.

    Args:
        authorization: Optional Authorization header

    Returns:
        User object if authenticated, None otherwise
    """
    if authorization is None:
        return None

    try:
        token = extract_token_from_header(authorization)
        auth_service = get_auth_service()
        user = await auth_service.authenticate_user_with_token(token)
        return user
    except (ValueError, HTTPException):
        return None


async def require_write_permission(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require user with write permissions.

    Args:
        current_user: Authenticated user from get_current_user

    Returns:
        User with write permissions

    Raises:
        HTTPException: If user lacks write permissions
    """
    if not current_user.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permissions required",
        )
    return current_user


async def require_communicate_capability(
    agent: Agent = Depends(get_current_agent),
) -> Agent:
    """
    Require agent with communicate capability.

    Args:
        agent: Authenticated agent from get_current_agent

    Returns:
        Agent with communicate capability

    Raises:
        HTTPException: If agent lacks communicate capability
    """
    if not agent.can_communicate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Communicate capability required",
        )
    return agent


async def require_meeting_capability(
    agent: Agent = Depends(get_current_agent),
) -> Agent:
    """
    Require agent with meeting creation capability.

    Args:
        agent: Authenticated agent from get_current_agent

    Returns:
        Agent with meeting creation capability

    Raises:
        HTTPException: If agent lacks meeting creation capability
    """
    if not agent.can_create_meetings:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting creation capability required",
        )
    return agent
