"""
MCP Broker Server - Inter-Claude Code Communication System

A centralized communication middleware that enables multiple Claude Code
instances to discover each other, negotiate communication capabilities,
and exchange messages using the Model Context Protocol (MCP).

Key Components:
- MCPServer: Main MCP server implementation
- MeetingMCPTools: Claude Code integration tools for meeting management
- HTTPClient: HTTP client for Communication Server API
"""

__version__ = "1.0.0"
__author__ = "MoAI Development Team"

# Core exports
from mcp_broker.core.config import BrokerConfig, get_config
from mcp_broker.core.logging import setup_logging, get_logger

# MCP Server exports
from mcp_broker.mcp.server import MCPServer
from mcp_broker.mcp.tools import MCPTools
from mcp_broker.mcp.meeting_tools import MeetingMCPTools

# HTTP Client exports
from mcp_broker.client.http_client import HTTPClient, CommunicationServerAPIError

# Component exports
from mcp_broker.session.manager import SessionManager
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.routing.router import MessageRouter
from mcp_broker.project.registry import ProjectRegistry

__all__ = [
    # Core
    "BrokerConfig",
    "get_config",
    "setup_logging",
    "get_logger",
    # MCP Server
    "MCPServer",
    "MCPTools",
    "MeetingMCPTools",
    # HTTP Client
    "HTTPClient",
    "CommunicationServerAPIError",
    # Components
    "SessionManager",
    "ProtocolRegistry",
    "MessageRouter",
    "ProjectRegistry",
]
