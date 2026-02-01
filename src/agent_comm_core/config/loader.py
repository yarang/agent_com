"""
Configuration file loader with multi-source merging.

Loads configuration from multiple sources and merges them in the following order:
1. Defaults (config.default.json in package)
2. User config (config.json in project root or /etc/agent-comm/)
3. Local overrides (config.local.json in project root, gitignored)
4. Environment variable overrides (highest priority)
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from agent_comm_core.config.models import Config


class ConfigLoader:
    """Load and merge configuration from multiple sources."""

    # Default search paths for configuration files (in priority order)
    DEFAULT_PATHS = [
        Path("/etc/agent-comm/config.json"),  # System-wide config
        Path.home() / ".config" / "agent-comm" / "config.json",  # User config
        Path.cwd() / "config.json",  # Project root config
    ]

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the configuration loader.

        Args:
            config_path: Optional path to a specific config file.
                        If provided, only this file will be used (plus defaults).
        """
        self.config_path = config_path
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from all sources.

        Returns:
            Validated Config object

        Raises:
            FileNotFoundError: If default config file is missing
            ValueError: If configuration is invalid
        """
        # Step 1: Load defaults
        config_dict = self._load_defaults()

        # Step 2: Merge user config (if any)
        user_config = self._find_and_load_user_config()
        if user_config:
            config_dict = self._deep_merge(config_dict, user_config)

        # Step 3: Merge local overrides (if any)
        local_config = self._load_local_config()
        if local_config:
            config_dict = self._deep_merge(config_dict, local_config)

        # Step 4: Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)

        # Step 5: Validate and create Config object
        self._config = Config(**config_dict)
        return self._config

    def reload(self) -> Config:
        """Reload configuration from all sources.

        Returns:
            Freshly loaded Config object
        """
        self._config = None
        return self.load()

    def _load_defaults(self) -> dict[str, Any]:
        """Load default configuration from package.

        Returns:
            Dictionary with default configuration

        Raises:
            FileNotFoundError: If default config file is missing
        """
        # Try package location first
        default_path = Path(__file__).parent / "config.default.json"

        if not default_path.exists():
            # Fallback to project root (for development)
            project_default = (
                Path.cwd() / "src" / "agent_comm_core" / "config" / "config.default.json"
            )
            if project_default.exists():
                default_path = project_default
            else:
                raise FileNotFoundError(f"Default configuration file not found at {default_path}")

        with open(default_path) as f:
            return json.load(f)

    def _find_and_load_user_config(self) -> Optional[dict[str, Any]]:
        """Find and load user configuration from default paths.

        Returns:
            User configuration dict, or None if not found
        """
        # If explicit path provided, use it
        if self.config_path:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    return json.load(f)
            return None

        # Search default paths
        for path in self.DEFAULT_PATHS:
            if path.exists():
                with open(path) as f:
                    return json.load(f)

        return None

    def _load_local_config(self) -> Optional[dict[str, Any]]:
        """Load local override configuration (gitignored).

        Returns:
            Local configuration dict, or None if not found
        """
        local_path = Path.cwd() / "config.local.json"
        if local_path.exists():
            with open(local_path) as f:
                return json.load(f)
        return None

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries.

        Values from override take precedence over base.
        Nested dictionaries are merged recursively.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override with new value
                result[key] = value

        return result

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to configuration.

        Environment variables use the following naming convention:
        - AGENT_COMM_<SECTION>_<KEY> for nested values
        - Flat names for common settings

        Example:
            AGENT_COMM_SERVER_PORT -> server.port
            AGENT_COMM_DATABASE_URL -> database.url
            DATABASE_URL -> database.url (legacy support)

        Args:
            config: Configuration dictionary

        Returns:
            Configuration dictionary with env overrides applied
        """
        # Define environment variable mappings
        env_mappings = {
            # Server settings
            "PORT": ("server", "port"),
            "AGENT_COMM_SERVER_PORT": ("server", "port"),
            "AGENT_COMM_SERVER_HOST": ("server", "host"),
            "HTTP_PORT": ("server", "port"),
            "SSL_PORT": ("server", "port"),
            # SSL settings
            "SSL_ENABLED": ("server", "ssl", "enabled"),
            "SSL_CERT_PATH": ("server", "ssl", "cert_path"),
            "SSL_KEY_PATH": ("server", "ssl", "key_path"),
            # CORS settings
            "CORS_ORIGINS": ("server", "cors", "origins"),
            # Database settings
            "DATABASE_URL": ("database", "url"),
            "AGENT_COMM_DATABASE_URL": ("database", "url"),
            # JWT settings
            "JWT_SECRET_KEY": ("authentication", "jwt", "secret_key"),
            "JWT_ALGORITHM": ("authentication", "jwt", "algorithm"),
            "ACCESS_TOKEN_EXPIRE_MINUTES": ("authentication", "jwt", "access_token_expire_minutes"),
            "REFRESH_TOKEN_EXPIRE_DAYS": ("authentication", "jwt", "refresh_token_expire_days"),
            # API token settings
            "API_TOKEN_SECRET": ("authentication", "api_token", "secret"),
            "API_TOKEN_PREFIX": ("authentication", "api_token", "prefix"),
            "AGENT_TOKEN": ("authentication", "api_token", "value"),
            # Agent settings
            "AGENT_NICKNAME": ("agent", "nickname"),
            "AGENT_PROJECT_ID": ("agent", "project_id"),
            # Communication server settings
            "COMMUNICATION_SERVER_URL": ("communication_server", "url"),
            "AGENT_COMM_SERVER_URL": ("communication_server", "url"),
            # Logging settings
            "MCP_BROKER_LOG_LEVEL": ("logging", "level"),
            "MCP_BROKER_LOG_FORMAT": ("logging", "format"),
        }

        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config, path, self._parse_env_value(value, path))

        return config

    def _set_nested_value(self, config: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
        """Set a nested value in config using path tuple.

        Args:
            config: Configuration dictionary
            path: Tuple of keys representing the path
            value: Value to set
        """
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def _parse_env_value(self, value: str, path: tuple[str, ...]) -> Any:
        """Parse environment variable value to appropriate type.

        Args:
            value: String value from environment
            path: Config path (for type hints)

        Returns:
            Parsed value (int, bool, list, or str)
        """
        # Check for boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Check for integer
        if path[-1] in (
            "port",
            "timeout",
            "pool_size",
            "max_overflow",
            "access_token_expire_minutes",
            "refresh_token_expire_days",
            "requests_per_minute",
        ):
            try:
                return int(value)
            except ValueError:
                pass

        # Check for list (comma-separated)
        if path[-1] in ("origins", "capabilities"):
            return [item.strip() for item in value.split(",") if item.strip()]

        return value


# Global config loader instance
_global_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance.

    Returns:
        ConfigLoader singleton instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader()
    return _global_loader


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration using the global loader.

    Args:
        config_path: Optional path to config file

    Returns:
        Validated Config object
    """
    loader = ConfigLoader(config_path)
    return loader.load()


def get_config() -> Config:
    """Get the cached configuration or load if not exists.

    Returns:
        Cached Config object
    """
    global _global_loader
    if _global_loader is None or _global_loader._config is None:
        _global_loader = ConfigLoader()
        return _global_loader.load()
    return _global_loader._config
