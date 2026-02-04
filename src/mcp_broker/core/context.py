"""
Request context management for MCP Broker Server.

This module provides the RequestContext class which maintains
request-scoped context including project identification, security
context, and metadata throughout the request lifecycle.

Context is stored using Python's contextvars module for thread-safe
async-safe storage that propagates automatically through async calls.
"""

import time
import typing
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from mcp_broker.core.logging import get_logger
from mcp_broker.core.security import SecurityContext
from mcp_broker.models.project import ProjectDefinition

logger = get_logger(__name__)

# Context variable for request-scoped context
# Using a sentinel object instead of None to avoid type issues
_sentinel = object()
_request_context: ContextVar[object] = ContextVar("request_context")


class RequestContext:
    """
    Request-scoped context for maintaining state throughout request lifecycle.

    The RequestContext stores project identification, security information,
    and metadata that needs to be accessible across the request processing
    pipeline without explicit parameter passing.

    Attributes:
        project_id: Project identifier for this request
        project: Full project definition (if available)
        security: Security context with authentication info
        request_id: Unique identifier for this request
        timestamp: When this context was created
        metadata: Additional context metadata
    """

    def __init__(
        self,
        project_id: str = "default",
        project: ProjectDefinition | None = None,
        security: SecurityContext | None = None,
        request_id: UUID | None = None,
    ):
        """Initialize request context.

        Args:
            project_id: Project identifier (defaults to "default")
            project: Full project definition if available
            security: Security context with authentication info
            request_id: Unique request identifier
        """
        self.project_id = project_id
        self.project = project
        self.security = security or SecurityContext(authenticated=False)
        self.request_id = request_id
        self.timestamp = time.time()
        self.metadata: dict = {}

    @property
    def is_authenticated(self) -> bool:
        """Check if the request is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.security.is_authenticated()

    @property
    def age_seconds(self) -> float:
        """Get the age of this context in seconds.

        Returns:
            Age in seconds since creation
        """
        return time.time() - self.timestamp

    def add_metadata(self, key: str, value: object) -> None:
        """Add metadata to the context.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: object = None) -> object:
        """Get metadata value from context.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def to_dict(self) -> dict:
        """Convert context to dictionary for logging.

        Returns:
            Dictionary representation of context
        """
        return {
            "project_id": self.project_id,
            "authenticated": self.is_authenticated,
            "session_id": str(self.security.session_id) if self.security.session_id else None,
            "request_id": str(self.request_id) if self.request_id else None,
            "age_seconds": self.age_seconds,
        }


def set_request_context(context: RequestContext) -> None:
    """Set the request context for the current async context.

    Args:
        context: RequestContext to set as current
    """
    _request_context.set(context)


def get_request_context() -> RequestContext:
    """Get the current request context.

    Returns:
        Current RequestContext

    Raises:
        RuntimeError: If no context is set
    """
    context = _request_context.get()
    if context is _sentinel or not isinstance(context, RequestContext):
        # Create default context if none exists
        context = RequestContext()
        _request_context.set(context)
    return context


def clear_request_context() -> None:
    """Clear the current request context."""
    _request_context.set(_sentinel)


@contextmanager
def request_context(
    project_id: str = "default",
    project: ProjectDefinition | None = None,
    security: SecurityContext | None = None,
) -> typing.Generator[RequestContext]:
    """Context manager for setting request context.

    Args:
        project_id: Project identifier
        project: Full project definition
        security: Security context

    Yields:
        RequestContext instance

    Example:
        >>> with request_context(project_id="my_project") as ctx:
        ...     # Process request with context
        ...     print(ctx.project_id)
    """
    context = RequestContext(
        project_id=project_id,
        project=project,
        security=security,
    )
    set_request_context(context)
    try:
        yield context
    finally:
        clear_request_context()


def get_current_project_id() -> str:
    """Get the project ID from current request context.

    Returns:
        Current project ID

    Raises:
        RuntimeError: If no context is set
    """
    context = get_request_context()
    return context.project_id


def get_current_project() -> ProjectDefinition | None:
    """Get the project definition from current request context.

    Returns:
        Current ProjectDefinition or None if not available
    """
    context = get_request_context()
    return context.project
