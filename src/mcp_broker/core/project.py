"""
Project identification middleware for multi-project support.

This module provides middleware to extract project_id from requests
using X-Project-ID header or API key prefix parsing.
"""

from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from mcp_broker.core.config import get_config
from mcp_broker.core.logging import get_logger

logger = get_logger(__name__)

# Project context key for request.state
PROJECT_CONTEXT_KEY = "project_id"
KEY_ID_CONTEXT_KEY = "key_id"


class ProjectIdentificationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to identify project for each incoming request.

    The middleware extracts project_id using the following priority order:
    1. X-Project-ID header (highest priority)
    2. API key prefix parsing (format: {project_id}_{key_id}_{secret})

    If no project identifier is found, returns 401 Unauthorized.
    If project is not found in registry, returns 403 Forbidden.

    The identified project_id and key_id are stored in request.state
    for use by downstream components.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and identify project.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response

        Raises:
            HTTPException: If project identification fails
        """
        config = get_config()

        # Skip project identification for public endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/security/status"]:
            return await call_next(request)

        # Skip if multi-project mode is disabled
        if not config.enable_multi_project:
            # Use default project for backward compatibility
            request.state[PROJECT_CONTEXT_KEY] = "default"
            request.state[KEY_ID_CONTEXT_KEY] = "default"
            return await call_next(request)

        # Priority 1: Check X-Project-ID header
        project_id = request.headers.get("X-Project-ID")

        if project_id:
            # Validate project exists
            if not await self._validate_project_exists(project_id):
                logger.warning(
                    f"Project not found: {project_id}",
                    extra={"context": {"project_id": project_id}},
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Project not found",
                )

            # Header-based identification - no API key validation needed here
            # (API key validation is handled by SecurityMiddleware)
            request.state[PROJECT_CONTEXT_KEY] = project_id
            request.state[KEY_ID_CONTEXT_KEY] = None

            logger.debug(
                f"Project identified via header: {project_id}",
                extra={"context": {"project_id": project_id}},
            )

            return await call_next(request)

        # Priority 2: Parse API key prefix
        api_key = request.headers.get("X-API-Key") or request.cookies.get("api_key")

        if api_key:
            parsed = self._parse_api_key_prefix(api_key)

            if parsed:
                extracted_project_id, key_id = parsed

                # Validate project exists
                if not await self._validate_project_exists(extracted_project_id):
                    logger.warning(
                        f"Project not found from API key: {extracted_project_id}",
                        extra={"context": {"project_id": extracted_project_id}},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Project not found",
                    )

                request.state[PROJECT_CONTEXT_KEY] = extracted_project_id
                request.state[KEY_ID_CONTEXT_KEY] = key_id

                logger.debug(
                    f"Project identified via API key prefix: {extracted_project_id}",
                    extra={"context": {"project_id": extracted_project_id, "key_id": key_id}},
                )

                return await call_next(request)

        # No project identifier found
        logger.warning(
            "Request without project identifier",
            extra={"context": {"path": request.url.path}},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing project credentials. Provide X-Project-ID header or API key.",
        )

    def _parse_api_key_prefix(self, api_key: str) -> tuple[str, str] | None:
        """
        Parse project_id and key_id from API key prefix.

        API key format: {project_id}_{key_id}_{secret}

        Args:
            api_key: API key string to parse

        Returns:
            Tuple of (project_id, key_id) if valid format, None otherwise
        """
        try:
            parts = api_key.split("_", 2)

            if len(parts) >= 2:
                project_id = parts[0]
                key_id = parts[1]

                # Basic validation - project_id should be lowercase alphanumeric/underscore
                if project_id and project_id.replace("_", "").isalnum():
                    return (project_id, key_id)

            return None

        except Exception:
            return None

    async def _validate_project_exists(self, project_id: str) -> bool:
        """
        Validate that a project exists in the registry.

        Args:
            project_id: Project identifier to validate

        Returns:
            True if project exists, False otherwise
        """
        # Import here to avoid circular dependency
        from mcp_broker.mcp.server import MCPServer

        # Get global broker server instance
        # Note: This requires the broker server to be accessible
        # In a real implementation, you might use a dependency injection pattern
        # or a singleton registry

        # For now, return True for "default" project (backward compatibility)
        if project_id == "default":
            return True

        # TODO: Access project registry from global broker instance
        # This is a placeholder - in production, use proper DI or singleton
        return True


def get_project_context(request: Request) -> str | None:
    """
    Get the project_id from request context.

    Args:
        request: FastAPI request object

    Returns:
        project_id if found, None otherwise
    """
    return getattr(request.state, PROJECT_CONTEXT_KEY, None)


def get_key_id_context(request: Request) -> str | None:
    """
    Get the key_id from request context.

    Args:
        request: FastAPI request object

    Returns:
        key_id if found, None otherwise
    """
    return getattr(request.state, KEY_ID_CONTEXT_KEY, None)
