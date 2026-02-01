"""
WebSocket authentication utilities.

Provides token-based authentication for WebSocket connections,
supporting both JWT tokens (dashboard users) and API tokens (agents).
"""

import logging
from typing import Optional, Union

from fastapi import WebSocket, status
from fastapi.websockets import WebSocketDisconnect

from agent_comm_core.models.auth import Agent, User

from communication_server.security.auth import AuthService, get_auth_service

logger = logging.getLogger(__name__)


class WebSocketAuth:
    """
    Authentication handler for WebSocket connections.

    Validates tokens via query parameter and returns authenticated
    User or Agent objects.
    """

    @staticmethod
    async def authenticate_websocket(
        websocket: WebSocket,
        token: Optional[str] = None,
    ) -> tuple[WebSocket, Union[User, Agent, None]]:
        """
        Authenticate a WebSocket connection.

        Accepts JWT tokens (for dashboard users) or API tokens (for agents).
        Token can be provided via query parameter.

        Args:
            websocket: WebSocket connection
            token: Authentication token (JWT or API token)

        Returns:
            tuple: (websocket, user_or_agent)

        Raises:
            WebSocketDisconnect: If authentication fails with WS_1008_POLICY_VIOLATION
        """
        if not token:
            logger.warning("WebSocket connection attempted without token")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication token required",
            )
            raise WebSocketDisconnect(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication token required",
            )

        auth_service = get_auth_service()

        # Try JWT token first (dashboard users)
        try:
            user = await auth_service.authenticate_user_with_token(token)
            if user:
                logger.info(f"WebSocket authenticated as user: {user.username}")
                return websocket, user
        except Exception as e:
            logger.debug(f"JWT token validation failed: {e}")

        # Try API token (agents)
        try:
            agent = await auth_service.authenticate_agent(token)
            if agent:
                logger.info(f"WebSocket authenticated as agent: {agent.nickname}")
                return websocket, agent
        except Exception as e:
            logger.debug(f"API token validation failed: {e}")

        # Authentication failed
        logger.warning("WebSocket authentication failed: Invalid token")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid authentication token",
        )
        raise WebSocketDisconnect(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid authentication token",
        )


def get_token_from_query(websocket: WebSocket) -> Optional[str]:
    """
    Extract token from WebSocket query parameters.

    Args:
        websocket: WebSocket connection

    Returns:
        Token string or None if not provided
    """
    return websocket.query_params.get("token")


async def get_current_user_from_token(token: str) -> Optional[User]:
    """
    Get authenticated user from JWT token.

    Helper function for WebSocket authentication.

    Args:
        token: JWT access token

    Returns:
        User object if token is valid, None otherwise
    """
    auth_service = get_auth_service()
    return await auth_service.authenticate_user_with_token(token)


async def get_current_agent_from_token(token: str) -> Optional[Agent]:
    """
    Get authenticated agent from API token.

    Helper function for WebSocket authentication.

    Args:
        token: API bearer token

    Returns:
        Agent object if token is valid, None otherwise
    """
    auth_service = get_auth_service()
    return await auth_service.authenticate_agent(token)
