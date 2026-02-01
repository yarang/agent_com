"""
Configuration management for MCP Broker Server.

This module provides centralized configuration using the shared
agent_comm_core configuration system with JSON files and
environment variable overrides.
"""

from agent_comm_core.config import Config, get_config


def get_broker_config() -> Config:
    """
    Get the configuration for MCP Broker.

    Returns:
        Config instance with all broker settings

    Example:
        >>> config = get_broker_config()
        >>> host = config.server.host
        >>> port = config.server.port
        >>> nickname = config.agent.nickname
    """
    return get_config()


# Backward compatibility wrapper for existing code
class BrokerConfig:
    """
    Backward compatibility wrapper for existing BrokerConfig usage.

    This class wraps the new Config system to maintain compatibility
    with existing code that uses the old BrokerConfig dataclass.

    Deprecated: Use get_config() from agent_comm_core.config instead.
    """

    def __init__(self, config: Config | None = None):
        """Initialize with optional config instance.

        Args:
            config: Config instance, or loads default if None
        """
        self._config = config or get_config()

    @property
    def host(self) -> str:
        """Get server host."""
        # For MCP broker, default to localhost if not specified
        return self._config.server.host

    @property
    def port(self) -> int:
        """Get server port (default 8000 for MCP broker)."""
        # Check if we should use the broker-specific port
        import os

        broker_port = os.getenv("MCP_BROKER_PORT")
        if broker_port:
            return int(broker_port)
        # Use server port from config
        return self._config.server.port

    @property
    def log_level(self) -> str:
        """Get log level."""
        return self._config.get_log_level()

    @property
    def log_format(self) -> str:
        """Get log format."""
        return self._config.get_log_format()

    @property
    def agent_nickname(self) -> str:
        """Get agent nickname."""
        return self._config.agent.nickname

    @property
    def agent_token(self) -> str:
        """Get agent token from config or environment."""
        if self._config.authentication.api_token.value:
            return self._config.authentication.api_token.value
        # Fallback to environment
        import os

        return os.getenv("AGENT_TOKEN", "")

    @property
    def agent_project_id(self) -> str:
        """Get agent project ID."""
        return self._config.agent.project_id

    @property
    def communication_server_url(self) -> str:
        """Get communication server URL."""
        return self._config.communication_server.url

    @property
    def storage_backend(self) -> str:
        """Get storage backend type."""
        import os

        return os.getenv("MCP_BROKER_STORAGE", "memory")

    @property
    def redis_url(self) -> str | None:
        """Get Redis URL."""
        import os

        return os.getenv("MCP_BROKER_REDIS_URL")

    @property
    def queue_capacity(self) -> int:
        """Get queue capacity."""
        import os

        return int(os.getenv("MCP_BROKER_QUEUE_CAPACITY", "100"))

    @property
    def queue_warning_threshold(self) -> float:
        """Get queue warning threshold."""
        import os

        return float(os.getenv("MCP_BROKER_QUEUE_WARNING", "0.9"))

    @property
    def heartbeat_interval(self) -> int:
        """Get heartbeat interval."""
        import os

        return int(os.getenv("MCP_BROKER_HEARTBEAT_INTERVAL", "30"))

    @property
    def stale_threshold(self) -> int:
        """Get stale threshold."""
        import os

        return int(os.getenv("MCP_BROKER_STALE_THRESHOLD", "30"))

    @property
    def disconnect_threshold(self) -> int:
        """Get disconnect threshold."""
        import os

        return int(os.getenv("MCP_BROKER_DISCONNECT_THRESHOLD", "60"))

    @property
    def max_payload_size_mb(self) -> int:
        """Get max payload size."""
        import os

        return int(os.getenv("MCP_BROKER_MAX_PAYLOAD_MB", "10"))

    @property
    def enable_auth(self) -> bool:
        """Get auth enabled flag."""
        import os

        return os.getenv("MCP_BROKER_ENABLE_AUTH", "false").lower() == "true"

    @property
    def auth_secret(self) -> str | None:
        """Get auth secret."""
        import os

        return os.getenv("MCP_BROKER_AUTH_SECRET")

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins."""
        # Use config server CORS origins
        return self._config.get_cors_origins()

    @property
    def enable_multi_project(self) -> bool:
        """Get multi-project enabled flag."""
        import os

        return os.getenv("MCP_BROKER_ENABLE_MULTI_PROJECT", "false").lower() == "true"


# Global configuration instance (backward compatibility)
_config: BrokerConfig | None = None


def get_config_legacy(**overrides) -> BrokerConfig:
    """
    Get the global BrokerConfig instance (legacy API).

    Args:
        **overrides: Configuration values to override (not supported in new system)

    Returns:
        The BrokerConfig wrapper instance

    Deprecated: Use get_config() from agent_comm_core.config instead.
    """
    global _config

    if _config is None:
        _config = BrokerConfig()

    return _config
