"""
Pydantic models for configuration validation.

These models provide type-safe configuration with validation
and default values for all configuration options.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class SSLConfig(BaseModel):
    """SSL/TLS configuration for HTTPS."""

    enabled: bool = False
    cert_path: str = "./certificates/cert.pem"
    key_path: str = "./certificates/key.pem"


class CORSConfig(BaseModel):
    """CORS configuration for cross-origin requests."""

    origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8000",
        ]
    )
    allow_credentials: bool = True


class ServerConfig(BaseModel):
    """Server configuration for Communication Server."""

    host: str = "0.0.0.0"
    port: int = 8001
    ssl: SSLConfig = Field(default_factory=SSLConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: str = "postgresql+asyncpg://agent:password@localhost:5432/agent_comm"
    pool_size: int = 10
    max_overflow: int = 20

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that database URL uses async driver."""
        if not v:
            raise ValueError("Database URL cannot be empty")
        if "postgresql" in v and "asyncpg" not in v:
            raise ValueError(
                "Database URL must use asyncpg driver for async operations. "
                "Use: postgresql+asyncpg://..."
            )
        return v


class JWTConfig(BaseModel):
    """JWT token configuration for user authentication."""

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that secret key is at least 32 characters."""
        if len(v) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 characters long. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v


class APITokenConfig(BaseModel):
    """API token configuration for agent authentication."""

    prefix: str = "agent_"
    secret: str = "change-me-in-production"
    value: str | None = Field(default=None, exclude=True)  # Not stored in config file


class AuthenticationConfig(BaseModel):
    """Authentication configuration for users and agents."""

    jwt: JWTConfig = Field(default_factory=JWTConfig)
    api_token: APITokenConfig = Field(default_factory=APITokenConfig)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = True
    requests_per_minute: int = 60


class HeadersConfig(BaseModel):
    """Security headers configuration."""

    enabled: bool = True


class SecurityConfig(BaseModel):
    """Security configuration for the server."""

    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    headers: HeadersConfig = Field(default_factory=HeadersConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "text"] = "json"


class AgentConfig(BaseModel):
    """Agent configuration for MCP Broker."""

    nickname: str = "AnonymousAgent"
    project_id: str = "agent-comm"
    capabilities: list[str] = Field(default_factory=list)


class CommunicationServerConfig(BaseModel):
    """Communication server connection configuration."""

    url: str = "http://localhost:8001"
    timeout: int = 30


class Config(BaseModel):
    """Root configuration model for the entire system."""

    version: str = "1.0.0"
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    communication_server: CommunicationServerConfig = Field(
        default_factory=CommunicationServerConfig
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format (basic check)."""
        if not v:
            raise ValueError("Version cannot be empty")
        return v

    def get_database_url(self) -> str:
        """Get the database URL."""
        return self.database.url

    def get_server_host(self) -> str:
        """Get the server host."""
        return self.server.host

    def get_server_port(self) -> int:
        """Get the server port."""
        return self.server.port

    def is_ssl_enabled(self) -> bool:
        """Check if SSL is enabled."""
        return self.server.ssl.enabled

    def get_cors_origins(self) -> list[str]:
        """Get CORS origins."""
        return self.server.cors.origins

    def get_log_level(self) -> str:
        """Get the log level."""
        return self.logging.level

    def get_log_format(self) -> str:
        """Get the log format."""
        return self.logging.format
