"""
Main entry point for MCP Broker Server.

Run the server using: python -m mcp_broker
"""

import argparse
import asyncio
import sys
from typing import Any

from mcp_broker.core.config import get_config
from mcp_broker.core.logging import get_logger, setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog="mcp_broker",
        description="MCP Broker Server for inter-Claude Code communication",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Server host address (default: from env or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: from env or 8000)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level (default: from env or INFO)",
    )
    parser.add_argument(
        "--log-format",
        choices=["json", "text"],
        default=None,
        help="Log format (default: from env or json)",
    )
    parser.add_argument(
        "--storage",
        choices=["memory", "redis"],
        default=None,
        help="Storage backend (default: from env or memory)",
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default=None,
        help="Redis connection URL (required if storage=redis)",
    )
    parser.add_argument(
        "--enable-auth",
        action="store_true",
        default=None,
        help="Enable authentication (default: from env)",
    )
    parser.add_argument(
        "--auth-secret",
        type=str,
        default=None,
        help="Authentication secret key",
    )
    parser.add_argument(
        "--cors-origins",
        type=str,
        default=None,
        help="Comma-separated list of allowed CORS origins",
    )
    # Agent configuration arguments
    parser.add_argument(
        "--agent-nickname",
        type=str,
        default=None,
        help="Agent display nickname (default: from env AGENT_NICKNAME)",
    )
    parser.add_argument(
        "--agent-token",
        type=str,
        default=None,
        help="API token for authentication (default: from env AGENT_TOKEN)",
    )
    parser.add_argument(
        "--agent-project-id",
        type=str,
        default=None,
        help="Project identifier (default: from env AGENT_PROJECT_ID)",
    )
    parser.add_argument(
        "--comm-server-url",
        type=str,
        default=None,
        dest="communication_server_url",
        help="Communication Server URL (default: from env COMMUNICATION_SERVER_URL)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )
    return parser.parse_args()


def args_to_config_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Convert command line args to config overrides.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary of config overrides
    """
    overrides: dict[str, Any] = {}

    if args.host is not None:
        overrides["host"] = args.host
    if args.port is not None:
        overrides["port"] = args.port
    if args.log_level is not None:
        overrides["log_level"] = args.log_level
    if args.log_format is not None:
        overrides["log_format"] = args.log_format
    if args.storage is not None:
        overrides["storage_backend"] = args.storage
    if args.redis_url is not None:
        overrides["redis_url"] = args.redis_url
    if args.enable_auth is not None:
        overrides["enable_auth"] = args.enable_auth
    if args.auth_secret is not None:
        overrides["auth_secret"] = args.auth_secret
    if args.cors_origins is not None:
        overrides["cors_origins"] = args.cors_origins.split(",")

    # Agent configuration overrides
    if args.agent_nickname is not None:
        overrides["agent_nickname"] = args.agent_nickname
    if args.agent_token is not None:
        overrides["agent_token"] = args.agent_token
    if args.agent_project_id is not None:
        overrides["agent_project_id"] = args.agent_project_id
    if args.communication_server_url is not None:
        overrides["communication_server_url"] = args.communication_server_url

    return overrides


async def _main_async() -> int:
    """Async main entry point for the MCP Broker Server.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command line arguments
    args = parse_args()

    # Get config with overrides
    overrides = args_to_config_overrides(args)
    config = get_config(**overrides)

    # Setup logging
    setup_logging(level=config.log_level, log_format=config.log_format)
    logger = get_logger(__name__)

    # Log startup configuration
    logger.info("Starting MCP Broker Server")
    logger.info(f"Host: {config.host}")
    logger.info(f"Port: {config.port}")
    logger.info(f"Storage: {config.storage_backend}")
    logger.info(f"Authentication: {'enabled' if config.enable_auth else 'disabled'}")
    logger.info(f"CORS origins: {config.cors_origins}")

    # Log agent configuration
    logger.info(f"Agent nickname: {config.agent_nickname}")
    logger.info(f"Agent project ID: {config.agent_project_id}")
    logger.info(f"Communication Server: {config.communication_server_url}")

    # Check for agent token
    if not config.agent_token:
        logger.warning(
            "WARNING: AGENT_TOKEN not configured. "
            "Please register your agent from the dashboard and set AGENT_TOKEN environment variable. "
            "Some features may not work without authentication."
        )
        print("\n" + "=" * 70)
        print("WARNING: AGENT_TOKEN not configured")
        print("=" * 70)
        print("\nPlease register your agent from the dashboard to get your API token.")
        print("\nThen set the AGENT_TOKEN environment variable:")
        print("  export AGENT_TOKEN='agent_agent-comm_xxxxx...'  # Linux/Mac")
        print("  set AGENT_TOKEN=agent_agent-comm_xxxxx...        # Windows")
        print("\nOr add it to your MCP configuration:")
        print('  "env": { "AGENT_TOKEN": "agent_agent-comm_xxxxx..." }')
        print("=" * 70 + "\n")
    else:
        logger.info("Agent token: configured (hidden for security)")

    # Import after logging is set up
    from mcp_broker.mcp.server import MCPServer

    # Create and run server
    server = MCPServer(config)

    try:
        await server.run()
        return 0
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        await server.stop()
        return 0
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        return 1


# Backward compatible alias
main = _main_async


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


# Synchronous entry point for uv scripts
def run_sync():
    """Synchronous entry point for package scripts."""
    sys.exit(asyncio.run(_main_async()))


if __name__ != "__main__":
    # When imported as module, export the sync runner
    main = run_sync  # type: ignore
