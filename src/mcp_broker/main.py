"""
FastAPI application entry point for MCP Broker Server.

Provides HTTP endpoints for health checks and testing.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_comm_core.config import get_config as get_core_config
from mcp_broker.core.config import BrokerConfig, get_config_legacy
from mcp_broker.core.logging import get_logger, setup_logging
from mcp_broker.core.security import SecurityMiddleware
from mcp_broker.mcp.server import MCPServer

# Global server instance
_broker_server: MCPServer | None = None
_global_config: BrokerConfig | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Manage application lifespan.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    global _broker_server, _global_config

    # Setup
    _global_config = get_config_legacy()
    setup_logging(level=_global_config.log_level, log_format=_global_config.log_format)

    logger = get_logger(__name__)
    logger.info("Starting MCP Broker Server (FastAPI mode)")
    logger.info(f"Authentication enabled: {_global_config.enable_auth}")
    logger.info(f"CORS origins: {_global_config.cors_origins}")

    # Log agent configuration
    logger.info(f"Agent nickname: {_global_config.agent_nickname}")
    logger.info(f"Agent project ID: {_global_config.agent_project_id}")
    logger.info(f"Communication Server: {_global_config.communication_server_url}")

    # Check for agent token
    if not _global_config.agent_token:
        logger.warning(
            "WARNING: AGENT_TOKEN not configured. "
            "Please register your agent from the dashboard and set AGENT_TOKEN environment variable. "
            "Some features may not work without authentication."
        )
    else:
        logger.info("Agent token: configured (hidden for security)")

    _broker_server = MCPServer(_global_config)
    await _broker_server.start_background_tasks()

    yield

    # Cleanup
    if _broker_server:
        await _broker_server.stop()
    logger.info("MCP Broker Server stopped")


# Create FastAPI app
app = FastAPI(
    title="MCP Broker Server",
    description="Inter-Claude Code communication system",
    version="1.0.0",
    lifespan=lifespan,
)


# Initialize config for middleware setup
_config = get_core_config()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add Security middleware if authentication is enabled
import os

if os.getenv("MCP_BROKER_ENABLE_AUTH", "false").lower() == "true":
    app.add_middleware(SecurityMiddleware)


# Response models


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    storage_backend: str
    active_sessions: int
    authentication_enabled: bool


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None


class SecurityStatusResponse(BaseModel):
    """Security status response."""

    authentication_enabled: bool
    cors_origins: list[str]
    recommendations: list[str]


# Endpoints


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse with server status
    """
    global _broker_server, _global_config

    if not _broker_server:
        raise HTTPException(status_code=503, detail="Server not initialized")

    sessions = await _broker_server.session_manager.list_sessions()
    active_count = len([s for s in sessions if s.status == "active"])

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        storage_backend=_broker_server.config.storage_backend,
        active_sessions=active_count,
        authentication_enabled=_global_config.enable_auth if _global_config else False,
    )


@app.get("/sessions", tags=["Sessions"])
async def list_sessions_api(
    status: str | None = None,
    include_capabilities: bool = True,
) -> dict[str, Any]:
    """List sessions via HTTP API.

    Args:
        status: Optional status filter
        include_capabilities: Include full capabilities

    Returns:
        Dict with sessions list
    """
    global _broker_server

    if not _broker_server:
        raise HTTPException(status_code=503, detail="Server not initialized")

    sessions = await _broker_server.session_manager.list_sessions(
        status_filter=status  # type: ignore
    )

    return {
        "sessions": [
            {
                "session_id": str(s.session_id),
                "connection_time": s.connection_time.isoformat(),
                "last_heartbeat": s.last_heartbeat.isoformat(),
                "status": s.status,
                "queue_size": s.queue_size,
                "capabilities": (s.capabilities.model_dump() if include_capabilities else None),
            }
            for s in sessions
        ],
        "count": len(sessions),
    }


@app.get("/protocols", tags=["Protocols"])
async def list_protocols_api(
    name: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """List protocols via HTTP API.

    Args:
        name: Optional name filter
        version: Optional version filter

    Returns:
        Dict with protocols list
    """
    global _broker_server

    if not _broker_server:
        raise HTTPException(status_code=503, detail="Server not initialized")

    protocols = await _broker_server.protocol_registry.discover(name=name, version=version)

    return {
        "protocols": [
            {
                "name": p.name,
                "version": p.version,
                "capabilities": p.capabilities,
                "metadata": p.metadata.model_dump() if p.metadata else None,
                "registered_at": p.registered_at.isoformat(),
            }
            for p in protocols
        ],
        "count": len(protocols),
    }


@app.get("/security/status", response_model=SecurityStatusResponse, tags=["Security"])
async def security_status() -> SecurityStatusResponse:
    """Get current security configuration and recommendations.

    Returns:
        SecurityStatusResponse with security status and recommendations
    """
    global _global_config

    if not _global_config:
        _global_config = get_config_legacy()

    recommendations: list[str] = []

    # Generate security recommendations
    if not _global_config.enable_auth:
        recommendations.append("Enable authentication for production use")

    if _global_config.enable_auth and not _global_config.auth_secret:
        recommendations.append("Set a secure auth_secret when authentication is enabled")

    if "*" in _global_config.cors_origins:
        recommendations.append("Restrict CORS origins to specific domains in production")

    if _global_config.cors_origins and len(_global_config.cors_origins) == 1:
        recommendations.append("Consider adding multiple allowed CORS origins")

    return SecurityStatusResponse(
        authentication_enabled=_global_config.enable_auth,
        cors_origins=_global_config.cors_origins,
        recommendations=recommendations,
    )


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with server info.

    Returns:
        Dict with server information
    """
    return {
        "name": "MCP Broker Server",
        "version": "1.0.0",
        "description": "Inter-Claude Code communication system",
        "docs": "/docs",
        "health": "/health",
        "security": "/security/status",
    }


if __name__ == "__main__":
    import uvicorn

    config = get_config_legacy()
    uvicorn.run(
        "mcp_broker.main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )
