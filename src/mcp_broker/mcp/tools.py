"""
MCP Tools for MCP Broker Server.

This module defines the six core MCP tools that expose
broker functionality to Claude Code instances.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from mcp.types import Tool
from pydantic import BaseModel, Field

from mcp_broker.core.logging import get_logger
from mcp_broker.models.message import Message, MessageHeaders
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.negotiation.negotiator import ProtocolRequirement

if TYPE_CHECKING:
    from mcp_broker.mcp.server import MCPServer

# Tool input schemas


class RegisterProtocolInput(BaseModel):
    """Input schema for register_protocol tool."""

    name: str = Field(description="Protocol identifier in snake_case")
    version: str = Field(description="Semantic version (e.g., '1.0.0')")
    schema: dict = Field(description="JSON Schema for message validation")
    capabilities: list[str] | None = Field(
        default=None,
        description="Supported communication patterns",
    )
    author: str | None = Field(default=None, description="Protocol author")
    description: str | None = Field(default=None, description="Protocol description")
    tags: list[str] | None = Field(default=None, description="Searchable tags")


class DiscoverProtocolsInput(BaseModel):
    """Input schema for discover_protocols tool."""

    name: str | None = Field(default=None, description="Filter by protocol name")
    version_range: str | None = Field(
        default=None, description="Semantic version range (e.g., '>=1.0.0,<2.0.0')"
    )
    tags: list[str] | None = Field(default=None, description="Filter by tags")


class NegotiateCapabilitiesInput(BaseModel):
    """Input schema for negotiate_capabilities tool."""

    target_session_id: str = Field(description="Target session UUID")
    required_protocols: list[dict] | None = Field(
        default=None, description="Required protocol versions"
    )


class SendMessageInput(BaseModel):
    """Input schema for send_message tool."""

    recipient_id: str = Field(description="Recipient session UUID")
    protocol_name: str = Field(description="Protocol for payload validation")
    protocol_version: str | None = Field(
        default=None, description="Protocol version (uses default if not specified)"
    )
    payload: dict = Field(description="Message payload")
    priority: str | None = Field(
        default="normal", description="Message priority (low, normal, high, urgent)"
    )
    ttl: int | None = Field(default=None, description="Time-to-live in seconds")


class BroadcastMessageInput(BaseModel):
    """Input schema for broadcast_message tool."""

    protocol_name: str = Field(description="Protocol for payload validation")
    protocol_version: str | None = Field(
        default=None, description="Protocol version (uses default if not specified)"
    )
    payload: dict = Field(description="Message payload")
    capability_filter: dict | None = Field(
        default=None, description="Filter recipients by capabilities"
    )
    priority: str | None = Field(
        default="normal", description="Message priority (low, normal, high, urgent)"
    )


class ListSessionsInput(BaseModel):
    """Input schema for list_sessions tool."""

    status_filter: str | None = Field(
        default="active",
        description="Filter sessions by status (active, stale, all)",
    )
    include_capabilities: bool | None = Field(
        default=True, description="Include full capability details"
    )


class MCPTools:
    """
    Collection of MCP tools for broker operations.

    This class defines the six core MCP tools:
    1. register_protocol - Register a new communication protocol
    2. discover_protocols - Query available protocols
    3. negotiate_capabilities - Perform capability handshake
    4. send_message - Send point-to-point message
    5. broadcast_message - Broadcast to all compatible sessions
    6. list_sessions - List active sessions
    """

    def __init__(self, broker: "MCPServer") -> None:
        """Initialize MCP tools with broker reference.

        Args:
            broker: MCPServer instance
        """
        self._broker = broker

    def get_tools(self) -> list[Tool]:
        """Get all MCP tools.

        Returns:
            List of Tool definitions
        """
        return [
            Tool(
                name="register_protocol",
                description="Register a new communication protocol with JSON Schema validation",
                inputSchema=RegisterProtocolInput.model_json_schema(),
            ),
            Tool(
                name="discover_protocols",
                description="Query available protocols with optional filtering by name, version range, or tags",
                inputSchema=DiscoverProtocolsInput.model_json_schema(),
            ),
            Tool(
                name="negotiate_capabilities",
                description="Perform capability negotiation handshake with a target session",
                inputSchema=NegotiateCapabilitiesInput.model_json_schema(),
            ),
            Tool(
                name="send_message",
                description="Send a point-to-point message to a specific session",
                inputSchema=SendMessageInput.model_json_schema(),
            ),
            Tool(
                name="broadcast_message",
                description="Broadcast a message to all sessions with compatible capabilities",
                inputSchema=BroadcastMessageInput.model_json_schema(),
            ),
            Tool(
                name="list_sessions",
                description="List all active sessions with their capabilities and status",
                inputSchema=ListSessionsInput.model_json_schema(),
            ),
            Tool(
                name="create_project",
                description="Create a new project with generated API keys",
                inputSchema={
                    "type": "object",
                    "required": ["project_id", "name"],
                    "properties": {
                        "project_id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*[a-z0-9]$"},
                        "name": {"type": "string", "minLength": 1, "maxLength": 100},
                        "description": {"type": "string", "maxLength": 500},
                        "max_sessions": {"type": "integer", "minimum": 1},
                        "max_protocols": {"type": "integer", "minimum": 1},
                        "allow_cross_project": {"type": "boolean"},
                        "discoverable": {"type": "boolean"},
                    },
                },
            ),
            Tool(
                name="list_projects",
                description="List discoverable projects with public metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name_filter": {"type": "string"},
                        "include_inactive": {"type": "boolean"},
                        "include_stats": {"type": "boolean"},
                    },
                },
            ),
            Tool(
                name="get_project_info",
                description="Get detailed project information",
                inputSchema={
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "include_config": {"type": "boolean"},
                        "include_permissions": {"type": "boolean"},
                    },
                },
            ),
            Tool(
                name="rotate_project_keys",
                description="Rotate project API keys (admin only)",
                inputSchema={
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "key_id": {"type": "string"},
                        "grace_period_seconds": {"type": "integer", "default": 300},
                    },
                },
            ),
            Tool(
                name="delete_project",
                description="Delete a project (soft delete, admin only)",
                inputSchema={
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                    },
                },
            ),
        ]

    async def register_protocol(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Register a new communication protocol.

        Args:
            input_data: Tool input with name, version, schema, capabilities

        Returns:
            Registration result with protocol info
        """
        # Parse input
        parsed = RegisterProtocolInput(**input_data)

        # Create protocol definition
        metadata = None
        if parsed.author or parsed.description or parsed.tags:
            from mcp_broker.models.protocol import ProtocolMetadata

            metadata = ProtocolMetadata(
                author=parsed.author,
                description=parsed.description,
                tags=parsed.tags or [],
            )

        protocol = ProtocolDefinition(
            name=parsed.name,
            version=parsed.version,
            message_schema=parsed.schema,
            capabilities=parsed.capabilities or ["point_to_point"],
            metadata=metadata,
        )

        # Register via protocol registry
        try:
            info = await self._broker.protocol_registry.register(protocol)

            return {
                "success": True,
                "protocol": {
                    "name": info.name,
                    "version": info.version,
                    "registered_at": info.registered_at.isoformat(),
                    "capabilities": info.capabilities,
                },
            }
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Registration failed: {e}",
            }

    async def discover_protocols(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Discover available protocols.

        Args:
            input_data: Tool input with optional filters

        Returns:
            List of matching protocols
        """
        parsed = DiscoverProtocolsInput(**input_data)

        protocols = await self._broker.protocol_registry.discover(
            name=parsed.name,
            version=parsed.version_range,
            tags=parsed.tags,
        )

        return {
            "protocols": [
                {
                    "name": p.name,
                    "version": p.version,
                    "capabilities": p.capabilities,
                    "metadata": p.metadata.model_dump() if p.metadata else None,
                }
                for p in protocols
            ],
            "count": len(protocols),
        }

    async def negotiate_capabilities(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Negotiate capabilities with target session.

        Args:
            input_data: Tool input with target_session_id

        Returns:
            Compatibility matrix
        """
        parsed = NegotiateCapabilitiesInput(**input_data)

        # Get current session (from context)
        current_session_id = self._broker.current_session_id
        if not current_session_id:
            return {"success": False, "error": "No current session"}

        # Get target session
        target_session_id = UUID(parsed.target_session_id)
        target_session = await self._broker.session_manager.get_session(target_session_id)
        if not target_session:
            return {"success": False, "error": "Target session not found"}

        # Get current session
        current_session = await self._broker.session_manager.get_session(current_session_id)
        if not current_session:
            return {"success": False, "error": "Current session not found"}

        # Parse required protocols
        required = None
        if parsed.required_protocols:
            required = [
                ProtocolRequirement(name=p["name"], version=p["version"])
                for p in parsed.required_protocols
            ]

        # Perform negotiation
        result = await self._broker.negotiator.negotiate(current_session, target_session, required)

        return {
            "compatible": result.compatible,
            "supported_protocols": result.supported_protocols,
            "feature_intersections": result.feature_intersections,
            "unsupported_features": result.unsupported_features,
            "incompatibilities": result.incompatibilities,
            "suggestion": result.suggestion,
        }

    async def send_message(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Send point-to-point message.

        Args:
            input_data: Tool input with recipient_id, payload

        Returns:
            Delivery result
        """
        parsed = SendMessageInput(**input_data)

        # Get current session
        current_session_id = self._broker.current_session_id
        if not current_session_id:
            return {"success": False, "error": "No current session"}

        # Create message
        message = Message(
            sender_id=current_session_id,
            recipient_id=UUID(parsed.recipient_id),
            protocol_name=parsed.protocol_name,
            protocol_version=parsed.protocol_version or "1.0.0",
            payload=parsed.payload,
            headers=MessageHeaders(priority=parsed.priority or "normal", ttl=parsed.ttl),
        )

        # Send message
        result = await self._broker.router.send_message(
            current_session_id, UUID(parsed.recipient_id), message
        )

        response = {
            "success": result.success,
            "message_id": str(result.message_id) if result.message_id else None,
        }

        if result.delivered_at:
            response["delivered_at"] = result.delivered_at.isoformat()

        if result.queued:
            response["queued"] = True
            response["queue_size"] = result.queue_size

        if result.error_reason:
            response["error"] = result.error_reason

        return response

    async def broadcast_message(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Broadcast message to compatible sessions.

        Args:
            input_data: Tool input with payload

        Returns:
            Broadcast result
        """
        parsed = BroadcastMessageInput(**input_data)

        # Get current session
        current_session_id = self._broker.current_session_id
        if not current_session_id:
            return {"success": False, "error": "No current session"}

        # Create broadcast message
        message = Message(
            sender_id=current_session_id,
            recipient_id=None,  # Broadcast
            protocol_name=parsed.protocol_name,
            protocol_version=parsed.protocol_version or "1.0.0",
            payload=parsed.payload,
            headers=MessageHeaders(priority=parsed.priority or "normal"),
        )

        # Broadcast
        result = await self._broker.router.broadcast_message(
            current_session_id, message, parsed.capability_filter
        )

        return {
            "success": result.success,
            "delivery_count": result.delivery_count,
            "recipients": {
                "delivered": [str(sid) for sid in result.recipients.get("delivered", [])],
                "failed": [str(sid) for sid in result.recipients.get("failed", [])],
                "skipped": [str(sid) for sid in result.recipients.get("skipped", [])],
            },
            "reason": result.reason,
        }

    async def list_sessions(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """List active sessions.

        Args:
            input_data: Tool input with filters

        Returns:
            List of sessions
        """
        parsed = ListSessionsInput(**input_data)

        # Map status filter
        status_filter: str | None = parsed.status_filter
        if status_filter == "all":
            status_filter = None

        sessions = await self._broker.session_manager.list_sessions(status_filter)

        return {
            "sessions": [
                {
                    "session_id": str(s.session_id),
                    "connection_time": s.connection_time.isoformat(),
                    "last_heartbeat": s.last_heartbeat.isoformat(),
                    "status": s.status,
                    "queue_size": s.queue_size,
                    "capabilities": (
                        s.capabilities.model_dump() if parsed.include_capabilities else None
                    ),
                }
                for s in sessions
            ],
            "count": len(sessions),
        }

    async def create_project(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new project with generated API keys.

        Args:
            input_data: Tool input with project_id, name, description, config

        Returns:
            Project creation result with credentials
        """
        from mcp_broker.models.project import ProjectConfig

        # Extract parameters
        project_id = input_data.get("project_id")
        name = input_data.get("name")
        description = input_data.get("description", "")
        tags = input_data.get("tags", [])

        # Build project config
        config_params = {}
        if "max_sessions" in input_data:
            config_params["max_sessions"] = input_data["max_sessions"]
        if "max_protocols" in input_data:
            config_params["max_protocols"] = input_data["max_protocols"]
        if "allow_cross_project" in input_data:
            config_params["allow_cross_project"] = input_data["allow_cross_project"]
        if "discoverable" in input_data:
            config_params["discoverable"] = input_data["discoverable"]

        config = ProjectConfig(**config_params) if config_params else None

        # Create project
        try:
            project = await self._broker.project_registry.create_project(
                project_id=project_id,
                name=name,
                description=description,
                config=config,
                tags=tags,
            )

            # Extract API keys for return (exclude secrets from logs)
            api_key_info = [
                {
                    "key_id": key.key_id,
                    "created_at": key.created_at.isoformat(),
                    "is_active": key.is_active,
                }
                for key in project.api_keys
            ]

            return {
                "success": True,
                "project": {
                    "project_id": project.project_id,
                    "name": project.metadata.name,
                    "description": project.metadata.description,
                    "status": project.status.status,
                    "created_at": project.status.created_at.isoformat(),
                },
                "api_keys": api_key_info,
                "credentials": {
                    "project_id": project.project_id,
                    "api_key": project.api_keys[0].api_key,  # Return first key for convenience
                },
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Project creation failed: {e}",
            }

    async def list_projects(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """List discoverable projects.

        Args:
            input_data: Tool input with optional filters

        Returns:
            List of projects
        """
        name_filter = input_data.get("name_filter")
        include_inactive = input_data.get("include_inactive", False)
        include_stats = input_data.get("include_stats", False)

        try:
            projects = await self._broker.project_registry.list_projects(
                name_filter=name_filter,
                include_inactive=include_inactive,
                include_stats=include_stats,
            )

            return {
                "success": True,
                "projects": [
                    {
                        "project_id": p.project_id,
                        "name": p.metadata.name,
                        "description": p.metadata.description,
                        "tags": p.metadata.tags,
                        "status": p.status,
                        "statistics": (
                            {
                                "session_count": p.statistics.session_count,
                                "message_count": p.statistics.message_count,
                                "protocol_count": p.statistics.protocol_count,
                                "last_activity": p.statistics.last_activity.isoformat(),
                            }
                            if include_stats
                            else None
                        ),
                    }
                    for p in projects
                ],
                "count": len(projects),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list projects: {e}",
            }

    async def get_project_info(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Get detailed project information.

        Args:
            input_data: Tool input with project_id

        Returns:
            Project details
        """
        project_id = input_data.get("project_id")
        include_config = input_data.get("include_config", False)
        include_permissions = input_data.get("include_permissions", False)

        try:
            project = await self._broker.project_registry.get_project(project_id)

            if not project:
                return {
                    "success": False,
                    "error": "Project not found",
                }

            result = {
                "success": True,
                "project": {
                    "project_id": project.project_id,
                    "name": project.metadata.name,
                    "description": project.metadata.description,
                    "tags": project.metadata.tags,
                    "owner": project.metadata.owner,
                    "status": project.status.status,
                    "created_at": project.status.created_at.isoformat(),
                    "last_modified": project.status.last_modified.isoformat(),
                },
            }

            if include_config:
                result["project"]["config"] = {
                    "max_sessions": project.config.max_sessions,
                    "max_protocols": project.config.max_protocols,
                    "max_message_queue_size": project.config.max_message_queue_size,
                    "allow_cross_project": project.config.allow_cross_project,
                    "discoverable": project.config.discoverable,
                    "shared_protocols": project.config.shared_protocols,
                }

            if include_permissions:
                result["project"]["cross_project_permissions"] = [
                    {
                        "target_project_id": perm.target_project_id,
                        "allowed_protocols": perm.allowed_protocols,
                        "message_rate_limit": perm.message_rate_limit,
                    }
                    for perm in project.cross_project_permissions
                ]

            # Always include statistics
            result["project"]["statistics"] = {
                "session_count": project.statistics.session_count,
                "message_count": project.statistics.message_count,
                "protocol_count": project.statistics.protocol_count,
                "last_activity": project.statistics.last_activity.isoformat(),
            }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get project info: {e}",
            }

    async def rotate_project_keys(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Rotate project API keys.

        Args:
            input_data: Tool input with project_id, optional key_id, grace_period

        Returns:
            Key rotation result
        """
        project_id = input_data.get("project_id")
        key_id = input_data.get("key_id")
        grace_period_seconds = input_data.get("grace_period_seconds", 300)

        try:
            new_keys = await self._broker.project_registry.rotate_api_keys(
                project_id=project_id,
                key_id=key_id,
                grace_period_seconds=grace_period_seconds,
            )

            return {
                "success": True,
                "new_keys": [
                    {
                        "key_id": key.key_id,
                        "created_at": key.created_at.isoformat(),
                        "is_active": key.is_active,
                        "api_key": key.api_key,  # Return new API key
                    }
                    for key in new_keys
                ],
                "grace_period_seconds": grace_period_seconds,
                "message": (
                    f"New API key(s) generated. Old keys will expire in {grace_period_seconds} seconds."
                ),
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Key rotation failed: {e}",
            }

    async def delete_project(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Delete a project (soft delete, admin only).

        Args:
            input_data: Tool input with project_id

        Returns:
            Project deletion result
        """
        project_id = input_data.get("project_id")

        try:
            # Attempt to delete project
            result = await self._broker.project_registry.delete_project(project_id=project_id)

            if result:
                logger = get_logger(__name__)
                logger.info(
                    f"Project deleted: {project_id}",
                    extra={"context": {"project_id": project_id}},
                )

                return {
                    "success": True,
                    "project_id": project_id,
                    "message": f"Project '{project_id}' has been deleted.",
                }
            else:
                return {
                    "success": False,
                    "error": f"Project '{project_id}' not found",
                }

        except ValueError as e:
            # Project has active resources
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Project deletion failed: {e}",
            }
