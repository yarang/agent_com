"""
Unit tests for Configuration module.

Tests configuration loading, validation, and overrides.
"""

import os

import pytest

from mcp_broker.core.config import BrokerConfig, get_config


class TestBrokerConfig:
    """Tests for BrokerConfig dataclass."""

    def test_default_config(self, monkeypatch) -> None:
        """Test default configuration values."""
        # Clear env vars to ensure defaults
        monkeypatch.delenv("MCP_BROKER_HOST", raising=False)
        monkeypatch.delenv("MCP_BROKER_PORT", raising=False)
        monkeypatch.delenv("MCP_BROKER_LOG_LEVEL", raising=False)
        monkeypatch.delenv("MCP_BROKER_STORAGE", raising=False)
        monkeypatch.delenv("MCP_BROKER_QUEUE_CAPACITY", raising=False)
        monkeypatch.delenv("MCP_BROKER_ENABLE_AUTH", raising=False)

        # Reset config
        import mcp_broker.core.config as config_module
        config_module._config = None

        config = BrokerConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.log_level == "INFO"
        assert config.storage_backend == "memory"
        assert config.queue_capacity == 100
        assert config.enable_auth is False

        # Reset config
        config_module._config = None

    def test_config_from_env_vars(self, monkeypatch) -> None:
        """Test configuration loading from environment variables."""
        monkeypatch.setenv("MCP_BROKER_HOST", "127.0.0.1")
        monkeypatch.setenv("MCP_BROKER_PORT", "9000")
        monkeypatch.setenv("MCP_BROKER_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MCP_BROKER_STORAGE", "redis")
        monkeypatch.setenv("MCP_BROKER_REDIS_URL", "redis://localhost:6379")
        monkeypatch.setenv("MCP_BROKER_ENABLE_AUTH", "true")
        monkeypatch.setenv("MCP_BROKER_AUTH_SECRET", "my_secret")

        # Need to reset config singleton
        import mcp_broker.core.config as config_module
        config_module._config = None

        config = BrokerConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.log_level == "DEBUG"
        assert config.storage_backend == "redis"
        assert config.redis_url == "redis://localhost:6379"
        assert config.enable_auth is True
        assert config.auth_secret == "my_secret"

        # Reset config
        config_module._config = None

    def test_config_validation_redis_without_url(self) -> None:
        """Test that Redis backend requires URL."""
        with pytest.raises(ValueError, match="redis_url is required"):
            BrokerConfig(storage_backend="redis", redis_url=None)

    def test_config_validation_invalid_queue_threshold(self) -> None:
        """Test that queue warning threshold must be between 0 and 1."""
        with pytest.raises(ValueError, match="queue_warning_threshold must be between 0 and 1"):
            BrokerConfig(queue_warning_threshold=1.5)

        with pytest.raises(ValueError, match="queue_warning_threshold must be between 0 and 1"):
            BrokerConfig(queue_warning_threshold=0)

    def test_config_validation_stale_threshold_gt_disconnect(self, monkeypatch) -> None:
        """Test that stale_threshold must be <= disconnect_threshold."""
        # Clear env vars
        monkeypatch.delenv("MCP_BROKER_STALE_THRESHOLD", raising=False)
        monkeypatch.delenv("MCP_BROKER_DISCONNECT_THRESHOLD", raising=False)

        with pytest.raises(ValueError, match="stale_threshold must be <= disconnect_threshold"):
            BrokerConfig(stale_threshold=60, disconnect_threshold=30)

    def test_config_validation_valid_queue_threshold(self) -> None:
        """Test that valid queue threshold passes validation."""
        config = BrokerConfig(queue_warning_threshold=0.9)
        assert config.queue_warning_threshold == 0.9

    def test_config_validation_valid_thresholds(self) -> None:
        """Test that valid thresholds pass validation."""
        config = BrokerConfig(stale_threshold=30, disconnect_threshold=60)
        assert config.stale_threshold == 30
        assert config.disconnect_threshold == 60

    def test_frozen_config_raises_error_on_mutation(self) -> None:
        """Test that config is frozen and cannot be modified."""
        config = BrokerConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.host = "localhost"

    def test_cors_origins_parsing(self, monkeypatch) -> None:
        """Test parsing of CORS origins from environment."""
        monkeypatch.setenv("MCP_BROKER_CORS_ORIGINS", "http://localhost:3000,https://example.com")

        # Reset config
        import mcp_broker.core.config as config_module
        config_module._config = None

        config = BrokerConfig()

        assert config.cors_origins == ["http://localhost:3000", "https://example.com"]

        # Reset config
        config_module._config = None

    def test_log_format_validation(self, monkeypatch) -> None:
        """Test log format from environment."""
        monkeypatch.setenv("MCP_BROKER_LOG_FORMAT", "text")

        # Reset config
        import mcp_broker.core.config as config_module
        config_module._config = None

        config = BrokerConfig()
        assert config.log_format == "text"

        # Reset config
        config_module._config = None


class TestGetConfig:
    """Tests for get_config function."""

    def setup_method(self):
        """Reset config singleton before each test."""
        import mcp_broker.core.config as config_module
        config_module._config = None

    def teardown_method(self):
        """Reset config singleton after each test."""
        import mcp_broker.core.config as config_module
        config_module._config = None

    def test_get_config_returns_singleton(self) -> None:
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_get_config_with_overrides(self) -> None:
        """Test that get_config applies overrides."""
        config = get_config(port=9000, log_level="DEBUG")

        # Singleton should remain unchanged
        default_config = get_config()
        assert default_config.port == 8000

        # Override config should have new values
        assert config.port == 9000
        assert config.log_level == "DEBUG"

    def test_get_config_multiple_overrides(self) -> None:
        """Test get_config with multiple overrides."""
        config = get_config(
            host="127.0.0.1",
            port=9000,
            log_level="DEBUG",
            enable_auth=True,
        )

        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.log_level == "DEBUG"
        assert config.enable_auth is True

    def test_get_config_override_preserves_other_values(self, monkeypatch) -> None:
        """Test that overrides preserve other config values."""
        # Clear env vars to ensure defaults
        monkeypatch.delenv("MCP_BROKER_HOST", raising=False)
        monkeypatch.delenv("MCP_BROKER_PORT", raising=False)
        monkeypatch.delenv("MCP_BROKER_LOG_LEVEL", raising=False)
        monkeypatch.delenv("MCP_BROKER_STORAGE", raising=False)

        # Reset config
        import mcp_broker.core.config as config_module
        config_module._config = None

        config = get_config(port=9000)

        # Original values should be preserved
        assert config.host == "0.0.0.0"
        assert config.log_level == "INFO"
        assert config.storage_backend == "memory"

        # Reset config
        config_module._config = None

    def test_get_config_override_with_none(self) -> None:
        """Test get_config with None override."""
        config = get_config(auth_secret=None)

        assert config.auth_secret is None

    def test_get_config_override_with_list(self) -> None:
        """Test get_config with list override."""
        config = get_config(cors_origins=["http://localhost:3000"])

        assert config.cors_origins == ["http://localhost:3000"]
