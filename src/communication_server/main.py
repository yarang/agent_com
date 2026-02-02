"""
FastAPI application entry point for Communication Server.

Provides REST API and WebSocket endpoints for agent communication,
meeting management, and sequential discussion coordination.
"""

import os
import ssl
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from agent_comm_core.config import Config, ConfigLoader
from agent_comm_core.db.database import close_db, get_engine, init_db
from communication_server.api import (
    agents_router,
    auth_router,
    chat_router,
    communications_router,
    decisions_router,
    i18n_router,
    mediators_router,
    meetings_router,
    messages_router,
    projects_db_router,
    projects_router,
    security_router,
    status_router,
)

# Import database models to register them with SQLAlchemy
from communication_server.security.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from communication_server.websocket.handler import WebSocketHandler
from communication_server.websocket.manager import ConnectionManager

# Load configuration
config_path = os.getenv("CONFIG_PATH")
config_loader = ConfigLoader(config_path=Path(config_path)) if config_path else ConfigLoader()
config: Config = config_loader.load()


# Global connection manager
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """
    Lifespan context manager for the FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    database_url = config.get_database_url()
    get_engine(database_url)  # Initialize engine

    # Create database tables
    await init_db(database_url=database_url, drop_all=False)

    yield

    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Communication Server",
    description="REST API and WebSocket server for AI Agent Communication System",
    version=config.version,
    lifespan=lifespan,
)

# Configure CORS from config
cors_origins = config.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=config.server.cors.allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
if config.security.headers.enabled:
    app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware if enabled
if config.security.rate_limiting.enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=config.security.rate_limiting.requests_per_minute,
    )

# Include API routers
app.include_router(agents_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(communications_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(i18n_router, prefix="/api/v1")
app.include_router(mediators_router, prefix="/api/v1")
app.include_router(meetings_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(projects_db_router, prefix="/api/v1/db")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(security_router, prefix="/api/v1")
app.include_router(status_router, prefix="/api/v1")

# Mount static files for dashboard
# Mount at root level to serve CSS/JS directly
# StaticFiles() should be mounted AFTER all API routes
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    # Mount specific subdirectories for direct access
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    # Keep /static for other files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns the current status of the server.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "communication-server",
            "version": config.version,
            "ssl_enabled": config.is_ssl_enabled(),
        }
    )


@app.get("/")
async def root():
    """
    Root endpoint - redirects to dashboard or returns API info.
    """
    from fastapi.responses import FileResponse

    dashboard_path = static_dir / "index.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))

    return JSONResponse(
        content={
            "name": "Communication Server",
            "version": config.version,
            "description": "REST API and WebSocket server for AI Agent Communication System",
            "ssl_enabled": config.is_ssl_enabled(),
            "endpoints": {
                "api": "/api/v1",
                "health": "/health",
                "websocket": "/ws/meetings/{meeting_id}",
                "status_websocket": "/ws/status",
                "chat_websocket": "/ws/chat/{room_id}",
                "docs": "/docs",
                "dashboard": "/static/index.html",
            },
        }
    )


@app.websocket("/ws/meetings/{meeting_id}")
async def websocket_meeting_endpoint(
    websocket: WebSocket, meeting_id: str, token: str | None = None
):
    """
    WebSocket endpoint for real-time meeting communication.

    Authentication required via token query parameter (JWT for users, API token for agents).

    Args:
        websocket: WebSocket connection
        meeting_id: Meeting ID (UUID string)
        token: Authentication token (JWT access token or API token)
    """
    from uuid import UUID

    try:
        meeting_uuid = UUID(meeting_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    handler = WebSocketHandler(connection_manager)
    await handler.handle_connection(websocket, meeting_uuid, token)


@app.websocket("/ws/status")
async def websocket_status_endpoint(websocket: WebSocket, token: str | None = None):
    """
    WebSocket endpoint for real-time status board updates.

    Authentication required via token query parameter (JWT for users, API token for agents).
    Broadcasts agent status changes, new communications, and meeting events.

    Args:
        websocket: WebSocket connection
        token: Authentication token (JWT access token or API token)
    """
    from communication_server.websocket.status_handler import get_status_handler

    handler = get_status_handler(connection_manager)
    await handler.handle_connection(websocket, token)


@app.websocket("/ws/chat/{room_id}")
async def websocket_chat_endpoint(websocket: WebSocket, room_id: str, token: str | None = None):
    """
    WebSocket endpoint for real-time chat room communication.

    Authentication required via token query parameter (JWT for users, API token for agents).
    Broadcasts messages, participant join/leave events, and typing indicators.

    Args:
        websocket: WebSocket connection
        room_id: Chat room ID (UUID string)
        token: Authentication token (JWT access token or API token)
    """
    from uuid import UUID

    from communication_server.websocket.chat_handler import ChatWebSocketHandler
    from communication_server.websocket.chat_manager import get_chat_manager

    try:
        room_uuid = UUID(room_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    chat_manager = get_chat_manager()
    handler = ChatWebSocketHandler(chat_manager)
    await handler.handle_connection(websocket, room_uuid, token)


def create_ssl_context():
    """
    Create SSL context for HTTPS connections.

    Returns:
        ssl.SSLContext: Configured SSL context, or None if SSL is disabled
    """
    if not config.is_ssl_enabled():
        return None

    # Verify certificate files exist
    cert_path = Path(config.server.ssl.cert_path)
    key_path = Path(config.server.ssl.key_path)

    if not cert_path.exists():
        raise FileNotFoundError(f"SSL certificate not found: {config.server.ssl.cert_path}")
    if not key_path.exists():
        raise FileNotFoundError(f"SSL private key not found: {config.server.ssl.key_path}")

    # Create SSL context with TLS 1.3
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Load certificate and key
    context.load_cert_chain(cert_path=str(cert_path), keyfile=str(key_path))

    # Configure secure cipher suites and options
    context.set_ciphers("ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256")
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1

    return context


def main():
    """Main entry point for the communication server."""
    import uvicorn

    # Prepare SSL parameters
    ssl_kwargs = {}
    if config.is_ssl_enabled():
        cert_path = Path(config.server.ssl.cert_path)
        key_path = Path(config.server.ssl.key_path)

        if cert_path.exists() and key_path.exists():
            ssl_kwargs["ssl_certfile"] = str(cert_path)
            ssl_kwargs["ssl_keyfile"] = str(key_path)
        else:
            print(
                f"Warning: SSL files not found. Cert: {cert_path.exists()}, Key: {key_path.exists()}"
            )
            print("Running without SSL...")

    if config.is_ssl_enabled() and ssl_kwargs:
        print("=" * 60)
        print("SSL/TLS is ENABLED")
        print(f"HTTPS endpoint: https://{config.server.host}:{config.server.port}")
        print(f"Secure WebSocket: wss://{config.server.host}:{config.server.port}/ws/status")
        print("=" * 60)
    else:
        print("=" * 60)
        print("SSL/TLS is DISABLED")
        print(f"HTTP endpoint: http://{config.server.host}:{config.server.port}")
        print(f"WebSocket: ws://{config.server.host}:{config.server.port}/ws/status")
        print("=" * 60)
        print("To enable SSL, set server.ssl.enabled=true in config.json and run:")
        print(
            "  ./scripts/setup-ssl.sh --production --domain yourdomain.com --email admin@example.com"
        )
        print("=" * 60)

    # Run the server
    # Note: SSL and reload are not compatible
    # In development with SSL, disable reload or use a separate process
    uvicorn.run(
        "communication_server.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=not config.is_ssl_enabled(),  # Disable reload when SSL is enabled
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
