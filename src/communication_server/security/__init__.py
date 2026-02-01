"""
Security module for Communication Server.

Provides JWT authentication, API token management, authentication
middleware, and protected route dependencies.
"""

from communication_server.security.auth import AuthService
from communication_server.security.dependencies import (
    get_current_active_user,
    get_current_agent,
    get_current_user,
    get_optional_user,
    oauth2_scheme,
    require_agent,
)
from communication_server.security.middleware import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
)
from communication_server.security.tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_agent_token,
    hash_api_token,
    validate_agent_token,
    verify_jwt_token,
)

__all__ = [
    # Auth Service
    "AuthService",
    # Dependencies
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_current_agent",
    "require_agent",
    "get_optional_user",
    # Middleware
    "AuthenticationMiddleware",
    "SecurityHeadersMiddleware",
    # Token Management
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_jwt_token",
    "generate_agent_token",
    "hash_api_token",
    "validate_agent_token",
]
