"""
MCP Server implementation for MCP Broker Server.

This module provides the MCPServer class that integrates the
broker components with the official MCP Python SDK.
"""

from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.server.stdio import stdio_server as stdio_server

from mcp_broker.client.http_client import HTTPClient
from mcp_broker.core.logging import get_logger
from mcp_broker.mcp.meeting_tools import MeetingMCPTools
from mcp_broker.mcp.tools import MCPTools
from mcp_broker.negotiation.negotiator import CapabilityNegotiator
from mcp_broker.project.registry import ProjectRegistry
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.routing.router import MessageRouter
from mcp_broker.session.manager import SessionManager
from mcp_broker.storage.memory import InMemoryStorage

logger = get_logger(__name__)


class MCPServer:
    """
    MCP Broker Server implementation.

    The MCPServer integrates all broker components and exposes
    them through the MCP protocol using the official Python SDK.

    Attributes:
        config: Broker configuration
        storage: Storage backend
        protocol_registry: Protocol registry
        session_manager: Session manager
        negotiator: Capability negotiator
        router: Message router
        tools: MCP tools collection (broker tools)
        meeting_tools: Meeting MCP tools (Claude Code integration)
        http_client: HTTP client for Communication Server
        current_session_id: Current session for tool calls
        agent_nickname: Agent's display nickname
        agent_token: API token for authentication
        agent_project_id: Project identifier
    """

    def __init__(
        self,
        config: Any = None,
        agent_id: str | None = None,
        communication_server_url: str | None = None,
    ) -> None:
        """Initialize the MCP Broker Server.

        Args:
            config: Optional broker configuration
            agent_id: This agent's ID (deprecated, use agent_nickname from config)
            communication_server_url: URL of the Communication Server (deprecated, use config)
        """
        import os

        from mcp_broker.core.config import get_config

        self.config = config or get_config()

        # Use agent configuration from config or environment
        self._agent_nickname = self.config.agent.nickname
        self._agent_token = self.config.authentication.api_token.value or os.getenv(
            "AGENT_TOKEN", ""
        )
        self._agent_project_id = self.config.agent.project_id
        self._communication_server_url = self.config.communication_server.url

        # For backward compatibility, support agent_id parameter
        self._agent_id = (
            agent_id or self._agent_nickname or os.getenv("AGENT_ID", "claude-code-agent")
        )

        # Initialize components
        self._storage = InMemoryStorage(
            queue_capacity=int(os.getenv("MCP_BROKER_QUEUE_CAPACITY", "100"))
        )
        self.protocol_registry = ProtocolRegistry(self._storage)
        self.session_manager = SessionManager(
            storage=self._storage,
            queue_capacity=int(os.getenv("MCP_BROKER_QUEUE_CAPACITY", "100")),
            stale_threshold=int(os.getenv("MCP_BROKER_STALE_THRESHOLD", "30")),
            disconnect_threshold=int(os.getenv("MCP_BROKER_DISCONNECT_THRESHOLD", "60")),
        )
        self.negotiator = CapabilityNegotiator()
        self.router = MessageRouter(self.session_manager, self._storage)
        self.project_registry = ProjectRegistry()

        # Tools collection
        self._tools = MCPTools(self)

        # HTTP Client for Communication Server integration
        self._http_client: HTTPClient | None = None

        # Meeting tools (initialized lazily)
        self._meeting_tools: MeetingMCPTools | None = None

        # Current session context (set per connection)
        self.current_session_id: UUID | None = None

        # MCP server instance
        self._server = Server("mcp-broker-server")

        # Register handlers
        self._register_handlers()

        logger.info(
            "MCPServer initialized",
            extra={
                "context": {
                    "config": self.config.__dict__,
                    "agent_nickname": self._agent_nickname,
                    "agent_project_id": self._agent_project_id,
                    "communication_server_url": self._communication_server_url,
                }
            },
        )

    @property
    def http_client(self) -> HTTPClient:
        """Get or create the HTTP client.

        Returns:
            The HTTPClient instance

        Raises:
            RuntimeError: If client cannot be initialized
        """
        if self._http_client is None:
            self._http_client = HTTPClient(
                base_url=self._communication_server_url,
                agent_token=self._agent_token,
                agent_nickname=self._agent_nickname,
            )
        return self._http_client

    @property
    def agent_id(self) -> str:
        """Get this agent's ID.

        Returns:
            Agent ID string
        """
        return self._agent_id

    @property
    def agent_nickname(self) -> str:
        """Get this agent's display nickname.

        Returns:
            Agent nickname string
        """
        return self._agent_nickname

    @property
    def agent_token(self) -> str:
        """Get this agent's API token.

        Returns:
            Agent token string
        """
        return self._agent_token

    @property
    def agent_project_id(self) -> str:
        """Get this agent's project ID.

        Returns:
            Project ID string
        """
        return self._agent_project_id

    @property
    def meeting_tools(self) -> MeetingMCPTools:
        """Get or create the meeting tools.

        Returns:
            The MeetingMCPTools instance
        """
        if self._meeting_tools is None:
            self._meeting_tools = MeetingMCPTools(
                http_client=self.http_client,
                agent_id=self._agent_id,
                agent_token=self._agent_token,
                agent_nickname=self._agent_nickname,
            )
        return self._meeting_tools

    def _register_handlers(self) -> None:
        """Register MCP server handlers."""

        @self._server.list_tools()
        async def handle_list_tools() -> list[dict[str, Any]]:
            """Handle list_tools request."""
            # Broker tools
            broker_tools = [
                {
                    "name": "register_protocol",
                    "description": "Register a new communication protocol with JSON Schema validation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "version": {"type": "string"},
                            "schema": {"type": "object"},
                            "capabilities": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "author": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "version", "schema"],
                    },
                },
                {
                    "name": "discover_protocols",
                    "description": "Query available protocols with optional filtering",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "version_range": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                {
                    "name": "negotiate_capabilities",
                    "description": "Perform capability negotiation with target session",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "target_session_id": {"type": "string"},
                            "required_protocols": {
                                "type": "array",
                                "items": {"type": "object"},
                            },
                        },
                        "required": ["target_session_id"],
                    },
                },
                {
                    "name": "broker_send_message",
                    "description": "Send point-to-point message to specific session (via broker)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "recipient_id": {"type": "string"},
                            "protocol_name": {"type": "string"},
                            "protocol_version": {"type": "string"},
                            "payload": {"type": "object"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "normal", "high", "urgent"],
                            },
                            "ttl": {"type": "integer"},
                        },
                        "required": ["recipient_id", "protocol_name", "payload"],
                    },
                },
                {
                    "name": "broadcast_message",
                    "description": "Broadcast message to all compatible sessions",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "protocol_name": {"type": "string"},
                            "protocol_version": {"type": "string"},
                            "payload": {"type": "object"},
                            "capability_filter": {"type": "object"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "normal", "high", "urgent"],
                            },
                        },
                        "required": ["protocol_name", "payload"],
                    },
                },
                {
                    "name": "list_sessions",
                    "description": "List all active sessions with capabilities",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "status_filter": {
                                "type": "string",
                                "enum": ["active", "stale", "all"],
                            },
                            "include_capabilities": {"type": "boolean"},
                        },
                    },
                },
                {
                    "name": "create_project",
                    "description": "Create a new project with generated API keys",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "max_sessions": {"type": "integer"},
                            "max_protocols": {"type": "integer"},
                            "allow_cross_project": {"type": "boolean"},
                            "discoverable": {"type": "boolean"},
                        },
                        "required": ["project_id", "name"],
                    },
                },
                {
                    "name": "list_projects",
                    "description": "List discoverable projects with public metadata",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name_filter": {"type": "string"},
                            "include_inactive": {"type": "boolean"},
                            "include_stats": {"type": "boolean"},
                        },
                    },
                },
                {
                    "name": "get_project_info",
                    "description": "Get detailed project information",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "include_config": {"type": "boolean"},
                            "include_permissions": {"type": "boolean"},
                        },
                        "required": ["project_id"],
                    },
                },
                {
                    "name": "rotate_project_keys",
                    "description": "Rotate project API keys (admin only)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "key_id": {"type": "string"},
                            "grace_period_seconds": {"type": "integer"},
                        },
                        "required": ["project_id"],
                    },
                },
            ]

            # Meeting tools (Claude Code integration)
            meeting_tools = self.meeting_tools.get_tool_definitions()

            return broker_tools + meeting_tools

        @self._server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
            """Handle call_tool request."""
            logger.info(
                f"Tool called: {name}",
                extra={"context": {"tool_name": name, "arguments": arguments}},
            )

            try:
                # Broker tools
                if name == "register_protocol":
                    result = await self._tools.register_protocol(arguments)
                elif name == "discover_protocols":
                    result = await self._tools.discover_protocols(arguments)
                elif name == "negotiate_capabilities":
                    result = await self._tools.negotiate_capabilities(arguments)
                elif name == "broker_send_message":
                    result = await self._tools.send_message(arguments)
                elif name == "broadcast_message":
                    result = await self._tools.broadcast_message(arguments)
                elif name == "list_sessions":
                    result = await self._tools.list_sessions(arguments)
                elif name == "create_project":
                    result = await self._tools.create_project(arguments)
                elif name == "list_projects":
                    result = await self._tools.list_projects(arguments)
                elif name == "get_project_info":
                    result = await self._tools.get_project_info(arguments)
                elif name == "rotate_project_keys":
                    result = await self._tools.rotate_project_keys(arguments)

                # Meeting tools (Claude Code integration)
                elif name == "send_message":
                    result = await self.meeting_tools.send_message(arguments)
                elif name == "create_meeting":
                    result = await self.meeting_tools.create_meeting(arguments)
                elif name == "join_meeting":
                    result = await self.meeting_tools.join_meeting(arguments)
                elif name == "get_decisions":
                    result = await self.meeting_tools.get_decisions(arguments)
                elif name == "propose_topic":
                    result = await self.meeting_tools.propose_topic(arguments)

                else:
                    return [
                        {
                            "type": "text",
                            "text": f"Unknown tool: {name}",
                        }
                    ]

                return [
                    {
                        "type": "text",
                        "text": str(result),
                    }
                ]

            except Exception as e:
                logger.error(
                    f"Tool error: {name}: {e}",
                    extra={"context": {"tool_name": name, "error": str(e)}},
                )
                return [
                    {
                        "type": "text",
                        "text": f"Error: {e}",
                    }
                ]

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting MCP Broker Server...")

        # Initialize HTTP client
        await self.http_client.ensure_client()

        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                self._server.create_initialization_options(),
            )

    async def start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        import asyncio

        async def cleanup_task() -> None:
            """Background task for session cleanup."""
            while True:
                try:
                    await asyncio.sleep(10)
                    await self.session_manager.check_stale_sessions()
                    await self.session_manager.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")

        # Start cleanup task
        asyncio.create_task(cleanup_task())
        logger.info("Background tasks started")

    async def stop(self) -> None:
        """Stop the MCP server and cleanup resources."""
        logger.info("Stopping MCP Broker Server...")

        # Close HTTP client
        if self._http_client:
            await self._http_client.close()

        # Cleanup resources
        self._storage = None
        logger.info("MCP Broker Server stopped")
