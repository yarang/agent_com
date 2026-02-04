"""
Project identification middleware for MCP Broker Server.

This module provides the ProjectIdentificationMiddleware class which
extracts project identification from incoming requests using multiple
sources in priority order:
1. X-Project-ID header
2. API key prefix (format: {project_id}_{key_id}_{secret})
3. Connection parameter
4. Fallback to "default" project

The middleware injects project context into the request state for
downstream components to use.
"""

from collections.abc import Callable
from typing import cast

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from mcp_broker.core.context import get_request_context
from mcp_broker.core.logging import get_logger
from mcp_broker.models.project import ProjectDefinition
from mcp_broker.project.registry import get_project_registry

logger = get_logger(__name__)


class ProjectIdentificationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to identify and validate project for every incoming request.

    Identification priority:
    1. X-Project-ID header (explicit project override)
    2. API key prefix parsing ({project_id}_{key_id}_{secret})
    3. Connection parameter (for WebSocket connections)
    4. Fallback to "default" project (backward compatibility)

    The middleware validates that the identified project exists and is active,
    then injects the project_id into the request context for downstream use.

    Attributes:
        require_identification: If True, reject requests without project ID
        allow_default_fallback: If True, use "default" project when no identification found
    """

    def __init__(
        self,
        app,
        require_identification: bool = False,
        allow_default_fallback: bool = True,
    ):
        """Initialize the project identification middleware.

        Args:
            app: FastAPI application instance
            require_identification: If True, reject requests without explicit project ID
            allow_default_fallback: If True, allow fallback to "default" project
        """
        super().__init__(app)
        self.require_identification = require_identification
        self.allow_default_fallback = allow_default_fallback

        logger.info(
            "ProjectIdentificationMiddleware initialized",
            extra={
                "context": {
                    "require_identification": require_identification,
                    "allow_default_fallback": allow_default_fallback,
                }
            },
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with project identification.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response

        Raises:
            HTTPException: If project identification fails or project is invalid
        """
        # Skip identification for public endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Extract project ID using priority order
        project_id = await self._extract_project_id(request)

        # Validate project exists and is active
        project = await self._validate_project(project_id)

        # Inject project context into request
        await self._inject_project_context(request, project_id, project)

        # Log successful identification
        logger.debug(
            f"Project identified: {project_id}",
            extra={"context": {"project_id": project_id, "path": request.url.path}},
        )

        # Continue processing
        return await call_next(request)

    async def _extract_project_id(self, request: Request) -> str:
        """Extract project ID from request using priority order.

        Priority:
        1. X-Project-ID header (highest priority)
        2. API key prefix parsing
        3. Query parameter
        4. Fallback to "default"

        Args:
            request: Incoming HTTP request

        Returns:
            Extracted project ID

        Raises:
            HTTPException: If no project ID can be determined and required
        """
        # 1. Check X-Project-ID header
        project_id_header = request.headers.get("X-Project-ID")
        if project_id_header:
            logger.debug(
                f"Project ID from header: {project_id_header}",
                extra={"context": {"project_id": project_id_header, "source": "header"}},
            )
            return project_id_header

        # 2. Parse API key prefix
        api_key = request.headers.get("X-API-Key") or request.cookies.get("api_key")
        if api_key:
            parsed_project_id = self._parse_api_key_prefix(api_key)
            if parsed_project_id:
                logger.debug(
                    f"Project ID from API key prefix: {parsed_project_id}",
                    extra={"context": {"project_id": parsed_project_id, "source": "api_key"}},
                )
                return parsed_project_id

        # 3. Check query parameter
        project_id_param = request.query_params.get("project_id")
        if project_id_param:
            logger.debug(
                f"Project ID from query parameter: {project_id_param}",
                extra={"context": {"project_id": project_id_param, "source": "query"}},
            )
            return project_id_param

        # 4. Fallback to "default" if allowed
        if self.allow_default_fallback:
            logger.debug(
                "No project ID found, using 'default'",
                extra={"context": {"source": "fallback"}},
            )
            return "default"

        # No project ID found and fallback not allowed
        logger.warning(
            "No project identification found in request",
            extra={"context": {"path": request.url.path, "client": str(request.client)}},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Project identification required. Provide X-Project-ID header or API key with project prefix.",
        )

    def _parse_api_key_prefix(self, api_key: str) -> str | None:
        """Parse project ID from API key prefix.

        API key format: {project_id}_{key_id}_{secret}

        Args:
            api_key: API key string

        Returns:
            Project ID if format is valid, None otherwise
        """
        try:
            parts = api_key.split("_", 2)
            if len(parts) == 3:
                project_id = parts[0]
                # Basic validation: project_id should be lowercase alphanumeric (no underscores)
                # Note: Project IDs with underscores will break this parser
                if project_id and project_id.isalnum():
                    return project_id
        except Exception:
            pass

        return None

    async def _validate_project(self, project_id: str) -> ProjectDefinition | None:
        """Validate that the project exists and is active.

        Args:
            project_id: Project identifier to validate

        Returns:
            ProjectDefinition if found and active, None otherwise

        Raises:
            HTTPException: If project not found or not active
        """
        registry = get_project_registry()

        # For "default" project, ensure it exists
        if project_id == "default":
            registry._ensure_default_project()

        project = await registry.get_project(project_id)

        if not project:
            logger.warning(
                f"Project not found: {project_id}",
                extra={"context": {"project_id": project_id}},
            )
            # Only raise if identification is required
            # Otherwise, allow graceful fallback behavior
            if self.require_identification:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Project '{project_id}' not found or access denied.",
                )
            return None

        # Check if project is active
        if not project.is_active():
            logger.warning(
                f"Project is not active: {project_id}",
                extra={"context": {"project_id": project_id, "status": project.status.status}},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Project '{project_id}' is not active.",
            )

        return project

    async def _inject_project_context(
        self,
        request: Request,
        project_id: str,
        project: ProjectDefinition | None,
    ) -> None:
        """Inject project context into request state.

        Args:
            request: HTTP request
            project_id: Project identifier
            project: Project definition (if found)
        """
        # Store in request state for downstream access
        request.state.project_id = project_id
        request.state.project = project

        # Update request context if it exists
        try:
            context = get_request_context()
            context.project_id = project_id
            context.project = project
        except Exception:
            # Context may not be initialized yet, which is fine
            pass


async def extract_project_id(request: Request) -> str:
    """Extract project ID from request state.

    Convenience function for downstream components to access
    the project ID identified by the middleware.

    Args:
        request: HTTP request

    Returns:
        Project ID from request state

    Raises:
        HTTPException: If project ID not found in request state
    """
    project_id = getattr(request.state, "project_id", None)
    if not project_id:
        logger.warning(
            "Project ID not found in request state",
            extra={"context": {"path": request.url.path}},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project identification middleware not properly configured.",
        )
    return cast(str, project_id)


async def get_project_from_request(request: Request) -> ProjectDefinition | None:
    """Get project definition from request state.

    Convenience function for downstream components to access
    the full project definition.

    Args:
        request: HTTP request

    Returns:
        ProjectDefinition if found, None otherwise
    """
    return getattr(request.state, "project", None)


def verify_project_access(
    request_project_id: str,
    target_project_id: str,
) -> bool:
    """Verify that a request can access a target project.

    This function enforces project boundary validation by checking
    that the request's project matches the target project.

    Args:
        request_project_id: Project ID from the incoming request
        target_project_id: Project ID being accessed

    Returns:
        True if access is allowed, False otherwise

    Note:
        Cross-project access requires explicit permission configuration
        which will be implemented in a future milestone.
    """
    if request_project_id == target_project_id:
        return True

    # Log cross-project access attempt
    logger.warning(
        f"Cross-project access attempt: {request_project_id} -> {target_project_id}",
        extra={
            "context": {
                "request_project_id": request_project_id,
                "target_project_id": target_project_id,
            }
        },
    )

    # For now, always deny cross-project access
    # Future implementation will check cross_project_permissions
    return False
