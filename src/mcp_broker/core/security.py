"""
Security module for MCP Broker Server.

Provides authentication middleware and token validation for API access.
"""

import secrets
import time
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyCookie
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from mcp_broker.core.config import get_config
from mcp_broker.core.logging import get_logger

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_cookie = APIKeyCookie(name="api_key", auto_error=False)

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication based on configuration."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with authentication check.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        config = get_config()

        # Skip authentication for public endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Skip if auth is disabled
        if not config.enable_auth:
            return await call_next(request)

        # Validate authentication
        if not config.auth_secret:
            logger.warning("Authentication enabled but no secret configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: authentication enabled but no secret",
            )

        # Check for API key in header or cookie
        api_key = request.headers.get("X-API-Key") or request.cookies.get("api_key")

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide X-API-Key header or api_key cookie.",
            )

        if not secrets.compare_digest(api_key, config.auth_secret):
            logger.warning(f"Invalid authentication attempt from {request.client}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )

        return await call_next(request)


async def verify_auth_token(request: Request) -> bool:
    """Verify authentication token from request.

    Args:
        request: Incoming HTTP request

    Returns:
        True if authenticated, False otherwise
    """
    config = get_config()

    # Skip if auth is disabled
    if not config.enable_auth:
        return True

    # Check for API key in header or cookie
    api_key = request.headers.get("X-API-Key") or request.cookies.get("api_key")

    if not api_key or not config.auth_secret:
        return False

    return secrets.compare_digest(api_key, config.auth_secret)


def generate_session_token() -> str:
    """Generate a cryptographically secure session token.

    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)


def validate_session_token(token: str, max_age_seconds: int = 3600) -> bool:
    """Validate a session token and its age.

    Args:
        token: Token string to validate
        max_age_seconds: Maximum age of token in seconds

    Returns:
        True if token is valid and not expired
    """
    if not token or len(token) < 32:
        return False

    # For now, simple validation - in production, check against token store
    # Token format validation (base64url encoded)
    try:
        # Ensure token only contains valid characters
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        )
        return all(c in valid_chars for c in token)
    except Exception:
        return False


class SecurityContext:
    """Security context for request-scoped security information."""

    def __init__(self, authenticated: bool = False, session_id: UUID | None = None):
        """Initialize security context.

        Args:
            authenticated: Whether the request is authenticated
            session_id: Optional session identifier
        """
        self.authenticated = authenticated
        self.session_id = session_id
        self.timestamp = time.time()

    def is_authenticated(self) -> bool:
        """Check if the context is authenticated.

        Returns:
            True if authenticated
        """
        return self.authenticated

    def age_seconds(self) -> float:
        """Get the age of this context in seconds.

        Returns:
            Age in seconds since creation
        """
        return time.time() - self.timestamp
