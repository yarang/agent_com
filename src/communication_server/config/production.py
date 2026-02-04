"""
Production configuration for Agent Communication Server.

This module provides production-ready settings with optimized
performance, security hardening, and proper monitoring.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ProductionConfig(BaseSettings):
    """Production configuration with security and performance optimizations."""

    # Application
    app_name: str = "Agent Communication Server"
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = Field(default=4, ge=1, le=32)
    reload: bool = False

    # Database (Connection Pooling)
    database_url: str = Field(
        ...,
        description="PostgreSQL database URL with asyncpg driver",
    )
    db_pool_size: int = Field(default=20, ge=5, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=50)
    db_pool_timeout: int = Field(default=30, ge=1, le=300)
    db_pool_recycle: int = Field(default=3600, ge=0, le=86400)
    db_echo: bool = False

    # Redis (Optional Caching)
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    redis_pool_size: int = Field(default=10, ge=1, le=50)
    redis_ttl: int = Field(default=3600, ge=60, le=86400)

    # Security
    secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT token signing",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=30)

    # CORS
    cors_origins: list[str] = Field(
        default=["https://app.example.com"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = Field(default=60, ge=10, le=1000)
    rate_limit_burst: int = Field(default=10, ge=1, le=100)

    # WebSocket
    websocket_max_connections: int = Field(default=100, ge=10, le=1000)
    websocket_ping_interval: int = Field(default=20, ge=5, le=120)
    websocket_ping_timeout: int = Field(default=30, ge=10, le=300)
    websocket_message_size_limit: int = Field(default=10485760, ge=1024, le=104857600)  # 10MB

    # Performance
    query_timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_request_size: int = Field(default=10485760, ge=1024, le=52428800)  # 10MB
    enable_response_compression: bool = True
    compression_level: int = Field(default=6, ge=1, le=9)

    # Monitoring & Logging
    enable_structured_logging: bool = True
    log_format: str = "json"  # json or text
    log_rotation: bool = True
    log_max_bytes: int = Field(default=10485760, ge=1048576, le=104857600)  # 10MB
    log_backup_count: int = Field(default=5, ge=1, le=20)
    enable_metrics: bool = True
    metrics_port: int = Field(default=9090, ge=1024, le=65535)

    # Tracing (Optional)
    enable_tracing: bool = False
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    tracing_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)

    # Feature Flags
    enable_topic_analyzer: bool = True
    enable_multi_round_discussion: bool = True
    max_discussion_rounds: int = Field(default=3, ge=1, le=10)
    consensus_threshold: float = Field(default=0.75, ge=0.5, le=1.0)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of {valid_environments}")
        return v

    class Config:
        env_file = ".env.production"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_production_config() -> ProductionConfig:
    """
    Get cached production configuration.

    Returns:
        ProductionConfig instance
    """
    return ProductionConfig()
