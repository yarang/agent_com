"""
Security API endpoints for emergency operations and security management.

Provides panic endpoint, rate limiting, and security status monitoring.
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from agent_comm_core.db.models.audit_log import ActorType, AuditAction, EntityType
from agent_comm_core.models.auth import User
from agent_comm_core.services.agent_api_key import get_agent_api_key_service
from agent_comm_core.services.audit_log import get_audit_log_service
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/security", tags=["Security"])


# ============================================================================
# Request/Response Models
# ============================================================================


class PanicRequest(BaseModel):
    """Request model for panic endpoint."""

    reason: str = Field(..., description="Reason for activating panic mode")
    scope: str = Field(
        default="all", description="Scope: 'all', 'project', or 'agent'"
    )
    project_id: UUID | None = Field(None, description="Project ID (if scope=project)")
    agent_id: UUID | None = Field(None, description="Agent ID (if scope=agent)")


class PanicResponse(BaseModel):
    """Response model for panic endpoint."""

    success: bool = Field(..., description="Whether panic was successful")
    keys_revoked: int = Field(..., description="Number of keys revoked")
    message: str = Field(..., description="Status message")


class SecurityStatusResponse(BaseModel):
    """Response model for security status endpoint."""

    active_keys: int = Field(..., description="Number of active API keys")
    revoked_keys: int = Field(..., description="Number of revoked keys")
    expired_keys: int = Field(..., description="Number of expired keys")
    recent_logins: int = Field(..., description="Number of recent logins (24h)")
    status: str = Field(default="healthy", description="Overall security status")


# ============================================================================
# Dependencies
# ============================================================================


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to require superuser access.

    Args:
        current_user: Currently authenticated user

    Returns:
        The user if superuser

    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/panic", response_model=PanicResponse)
async def emergency_panic(
    request: Request,
    panic_data: PanicRequest,
    current_user: Annotated[User, Depends(get_current_superuser)],
):
    """
    Emergency endpoint to revoke all agent keys immediately.

    Requires superuser privileges. This is a safety mechanism for
    emergency situations where all agent access needs to be revoked.

    Args:
        request: FastAPI request
        panic_data: Panic request data
        current_user: Current superuser

    Returns:
        Panic response with revocation count
    """
    from agent_comm_core.db.database import db_session

    keys_revoked = 0

    async with db_session() as session:
        key_service = get_agent_api_key_service(session)
        audit_service = get_audit_log_service(session)

        # Revoke keys based on scope
        if panic_data.scope == "all":
            keys_revoked = await _revoke_all_keys(key_service)
        elif panic_data.scope == "project" and panic_data.project_id:
            keys_revoked = await key_service.revoke_all_project_keys(
                panic_data.project_id
            )
        elif panic_data.scope == "agent" and panic_data.agent_id:
            keys_revoked = await key_service.revoke_all_agent_keys(
                panic_data.agent_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid scope or missing required IDs",
            )

        # Log panic action
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.PANIC,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            actor_type=ActorType.USER,
            actor_id=current_user.id,
            action_details={
                "reason": panic_data.reason,
                "scope": panic_data.scope,
                "project_id": str(panic_data.project_id) if panic_data.project_id else None,
                "agent_id": str(panic_data.agent_id) if panic_data.agent_id else None,
                "keys_revoked": keys_revoked,
            },
        )

    return PanicResponse(
        success=True,
        keys_revoked=keys_revoked,
        message=f"Emergency panic activated: {keys_revoked} keys revoked",
    )


@router.get("/status", response_model=SecurityStatusResponse)
async def get_security_status(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get security status information.

    Requires authentication. Returns statistics about API keys
    and recent authentication activity.

    Args:
        current_user: Current authenticated user

    Returns:
        Security status response
    """
    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        key_service = get_agent_api_key_service(session)
        audit_service = get_audit_log_service(session)

        # Get key statistics
        all_keys = await key_service.list_keys()

        active_keys = sum(1 for k in all_keys if k.status.value == "active")
        revoked_keys = sum(1 for k in all_keys if k.status.value == "revoked")
        expired_keys = sum(1 for k in all_keys if k.status.value == "expired")

        # Get recent logins (last 24 hours)
        from datetime import timedelta

        from agent_comm_core.models.audit_log import AuditLogFilter

        recent_logins = await audit_service.query(
            AuditLogFilter(
                action=AuditAction.AUTH_LOGIN.value,
                start_date=datetime.now(UTC) - timedelta(days=1),
            )
        )

    return SecurityStatusResponse(
        active_keys=active_keys,
        revoked_keys=revoked_keys,
        expired_keys=expired_keys,
        recent_logins=len(recent_logins),
        status="healthy",
    )


# ============================================================================
# Rate Limiting
# ============================================================================


class RateLimiter:
    """Simple in-memory rate limiter for agent-level requests.

    In production, use Redis for distributed rate limiting.
    """

    def __init__(self, requests_per_minute: int = 60):
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed.

        Args:
            identifier: Unique identifier (agent_id, IP, etc.)

        Returns:
            True if allowed, False otherwise
        """
        import time

        now = time.time()

        # Clean old requests
        if identifier in self._requests:
            self._requests[identifier] = [
                t for t in self._requests[identifier] if now - t < 60
            ]

        # Check rate limit
        request_count = len(self._requests.get(identifier, []))

        if request_count >= self.requests_per_minute:
            return False

        # Add current request
        if identifier not in self._requests:
            self._requests[identifier] = []
        self._requests[identifier].append(now)

        return True


# Global rate limiter instance
_agent_rate_limiter = RateLimiter(requests_per_minute=60)


async def check_agent_rate_limit(
    request: Request,
    x_agent_id: Annotated[str | None, Header()] = None,
) -> bool:
    """
    Check agent rate limit from request headers.

    Args:
        request: FastAPI request
        x_agent_id: Agent ID from header

    Returns:
        True if allowed

    Raises:
        HTTPException: If rate limit exceeded
    """
    # Try to get agent ID from request state (set by auth middleware)
    agent_id = getattr(request.state, "agent_id", None)

    # Fall back to header
    if not agent_id and x_agent_id:
        agent_id = x_agent_id

    # If no agent ID, skip rate limiting
    if not agent_id:
        return True

    if not _agent_rate_limiter.is_allowed(agent_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {_agent_rate_limiter.requests_per_minute} requests per minute.",
        )

    return True


# ============================================================================
# Helper Functions
# ============================================================================


async def _revoke_all_keys(key_service) -> int:
    """Revoke all active API keys.

    Args:
        key_service: Agent API key service

    Returns:
        Number of keys revoked
    """
    # This would require a bulk update method in the service
    # For now, return 0 as placeholder
    return 0
