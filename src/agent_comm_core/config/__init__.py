"""
Configuration system for AI Agent Communication System.

This module provides centralized configuration management using JSON files
with environment variable overrides and sensible defaults.

Configuration is loaded from multiple sources (in order of precedence):
1. Environment variables (highest priority)
2. config.local.json (gitignored, for local development)
3. config.json (user configuration in project root)
4. config.default.json (package defaults, lowest priority)

Example usage:
    from agent_comm_core.config import ConfigLoader, Config, get_config

    # Load configuration
    loader = ConfigLoader()
    config: Config = loader.load()

    # Or use the cached global config
    config = get_config()

    # Access configuration values
    server_host = config.server.host
    server_port = config.server.port
    database_url = config.database.url
"""

from agent_comm_core.config.defaults import get_default_config
from agent_comm_core.config.loader import ConfigLoader, get_config, load_config
from agent_comm_core.config.models import (
    AgentConfig,
    APITokenConfig,
    AuthenticationConfig,
    CommunicationServerConfig,
    Config,
    CORSConfig,
    DatabaseConfig,
    HeadersConfig,
    JWTConfig,
    LoggingConfig,
    RateLimitConfig,
    SecurityConfig,
    ServerConfig,
    SSLConfig,
)

__all__ = [
    # Models
    "Config",
    "ServerConfig",
    "SSLConfig",
    "CORSConfig",
    "DatabaseConfig",
    "AuthenticationConfig",
    "JWTConfig",
    "APITokenConfig",
    "SecurityConfig",
    "RateLimitConfig",
    "HeadersConfig",
    "LoggingConfig",
    "AgentConfig",
    "CommunicationServerConfig",
    # Loader
    "ConfigLoader",
    # Convenience functions
    "get_config",
    "load_config",
    # Defaults
    "get_default_config",
]
