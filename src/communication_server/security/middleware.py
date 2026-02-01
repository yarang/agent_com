"""
Authentication and security middleware for FastAPI.

Provides middleware for token validation, user context injection,
and security headers.
"""

from collections.abc import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from agent_comm_core.models.auth import Agent, User
from communication_server.security.auth import get_auth_service
from communication_server.security.tokens import extract_token_from_header


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for FastAPI.

    Extracts and validates tokens from the Authorization header,
    adding the authenticated user or agent to the request state.
    """

    def __init__(self, app, require_auth: bool = False):
        """
        Initialize the authentication middleware.

        Args:
            app: FastAPI application instance
            require_auth: If True, all endpoints require authentication
        """
        super().__init__(app)
        self.require_auth = require_auth

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the authentication middleware.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from the next handler
        """
        # Try to authenticate as user or agent
        authorization = request.headers.get("Authorization")

        if authorization:
            try:
                token = extract_token_from_header(authorization)
                auth_service = get_auth_service()

                # Try user authentication first (JWT)
                user = await auth_service.authenticate_user_with_token(token)
                if user:
                    request.state.user = user
                    request.state.auth_type = "user"
                else:
                    # Try agent authentication (API token)
                    agent = await auth_service.authenticate_agent(token)
                    if agent:
                        request.state.agent = agent
                        request.state.auth_type = "agent"

            except (ValueError, HTTPException):
                # Invalid token format, continue without auth
                pass

        # Check if authentication is required
        if (
            self.require_auth
            and getattr(request.state, "user", None) is None
            and getattr(request.state, "agent", None) is None
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Continue to next middleware or route handler
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for FastAPI.

    Adds security-related HTTP headers to all responses following
    OWASP security best practices.
    """

    # Security headers
    HEADERS = {
        # Prevents MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        # Prevents clickjacking attacks
        "X-Frame-Options": "DENY",
        # Enables browser XSS filter
        "X-XSS-Protection": "1; mode=block",
        # Content Security Policy (restricts resource sources)
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # Strict Transport Security (HTTPS only)
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        # Permissions policy
        "Permissions-Policy": (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        ),
    }

    def __init__(self, app):
        """
        Initialize the security headers middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Add security headers to response
        for header_name, header_value in self.HEADERS.items():
            response.headers[header_name] = header_value

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware for authentication endpoints.

    Prevents brute force attacks on login and token endpoints.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize the rate limiting middleware.

        Args:
            app: FastAPI application instance
            requests_per_minute: Maximum requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        # In-memory storage (replace with Redis in production)
        self._request_counts: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from the next handler

        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Get current time
        import time

        current_time = time.time()

        # Clean old requests (older than 1 minute)
        if client_ip in self._request_counts:
            self._request_counts[client_ip] = [
                t for t in self._request_counts[client_ip] if current_time - t < 60
            ]

        # Check rate limit
        request_count = len(self._request_counts.get(client_ip, []))

        if request_count >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
            )

        # Add current request
        if client_ip not in self._request_counts:
            self._request_counts[client_ip] = []
        self._request_counts[client_ip].append(current_time)

        # Continue to next middleware or route handler
        response = await call_next(request)
        return response


def get_current_user_from_request(request: Request) -> User | None:
    """
    Get the current authenticated user from request state.

    Helper function to access the user added by AuthenticationMiddleware.

    Args:
        request: FastAPI request object

    Returns:
        User object if authenticated, None otherwise
    """
    return getattr(request.state, "user", None)


def get_current_agent_from_request(request: Request) -> Agent | None:
    """
    Get the current authenticated agent from request state.

    Helper function to access the agent added by AuthenticationMiddleware.

    Args:
        request: FastAPI request object

    Returns:
        Agent object if authenticated, None otherwise
    """
    return getattr(request.state, "agent", None)
