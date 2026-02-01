"""
Default configuration values for the AI Agent Communication System.

This module provides default configuration that is used when
no custom configuration is provided.
"""

from agent_comm_core.config.models import Config


def get_default_config() -> dict:
    """Get the default configuration as a dictionary.

    Returns:
        Dictionary with default configuration values
    """
    return {
        "version": "1.0.0",
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "ssl": {
                "enabled": False,
                "cert_path": "./certificates/cert.pem",
                "key_path": "./certificates/key.pem",
            },
            "cors": {
                "origins": ["http://localhost:3000", "http://localhost:8000"],
                "allow_credentials": True,
            },
        },
        "database": {
            "url": "postgresql+asyncpg://agent:password@localhost:5432/agent_comm",
            "pool_size": 10,
            "max_overflow": 20,
        },
        "authentication": {
            "jwt": {
                # 32+ character default for development (change in production!)
                "secret_key": "dev-secret-key-32-chars-long-min",
                "algorithm": "HS256",
                "access_token_expire_minutes": 15,
                "refresh_token_expire_days": 7,
            },
            "api_token": {
                "prefix": "agent_",
                # 32+ character default for development (change in production!)
                "secret": "dev-api-token-secret-32-chars-min",
            },
        },
        "security": {
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 60,
            },
            "headers": {
                "enabled": True,
            },
        },
        "logging": {
            "level": "INFO",
            "format": "json",
        },
        "agent": {
            "nickname": "AnonymousAgent",
            "project_id": "agent-comm",
            "capabilities": [],
        },
        "communication_server": {
            "url": "http://localhost:8000",
            "timeout": 30,
        },
    }


# Create default Config instance (for direct use without file loading)
DEFAULT_CONFIG = Config(**get_default_config())
