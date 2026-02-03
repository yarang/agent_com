"""
Authentication and authorization models.

Pydantic models for users, agents, tokens, and authentication data.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class Token(BaseModel):
    """Response model for token creation."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user: Optional["User"] = Field(None, description="User information")


class TokenData(BaseModel):
    """Data extracted from JWT token."""

    user_id: str | None = None
    agent_id: str | None = None
    exp: int | None = None
    type: str | None = None


class User(BaseModel):
    """User model for dashboard authentication."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username", min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.USER, description="User role")
    permissions: list[str] = Field(default_factory=list, description="Granted permissions")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Account creation time"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def can_write(self) -> bool:
        """Check if user has write permissions."""
        return self.role in (UserRole.ADMIN, UserRole.USER)


class Agent(BaseModel):
    """Agent model for API token authentication."""

    id: UUID = Field(default_factory=uuid4, description="Unique agent identifier")
    project_id: str = Field(..., description="Project ID", min_length=1)
    nickname: str = Field(..., description="Agent display name", min_length=1, max_length=100)
    token: str = Field(..., description="Hashed API token")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Agent capabilities/permissions",
    )
    is_active: bool = Field(default=True, description="Whether agent is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Agent creation time")
    last_used: datetime | None = Field(None, description="Last authentication timestamp")

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        """Validate nickname format."""
        if not v or not v.strip():
            raise ValueError("Nickname cannot be empty")
        return v.strip()

    @property
    def can_communicate(self) -> bool:
        """Check if agent can send/receive communications."""
        return "communicate" in self.capabilities and self.is_active

    @property
    def can_create_meetings(self) -> bool:
        """Check if agent can create meetings."""
        return "create_meetings" in self.capabilities and self.is_active


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str = Field(..., description="Username", min_length=1)
    password: str = Field(..., description="Password", min_length=12)


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="Valid refresh token")


class AgentTokenCreate(BaseModel):
    """Request model for creating agent token."""

    project_id: str = Field(..., description="Project ID", min_length=1)
    nickname: str = Field(..., description="Agent display name", min_length=1, max_length=100)
    capabilities: list[str] = Field(
        default_factory=lambda: ["communicate"],
        description="Agent capabilities",
    )


class AgentTokenResponse(BaseModel):
    """Response model for agent token creation."""

    token: str = Field(..., description="API token (show only on creation)")
    agent_id: UUID = Field(..., description="Agent ID")
    message: str = Field(
        default="Store this token securely. It will not be shown again.",
        description="Security warning",
    )


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""

    current_password: str = Field(..., description="Current password", min_length=12)
    new_password: str = Field(..., description="New password", min_length=12)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        return v


class UserCreate(BaseModel):
    """Request model for creating a new user."""

    username: str = Field(..., description="Username", min_length=1, max_length=100)
    password: str = Field(..., description="Password", min_length=12)
    role: UserRole = Field(default=UserRole.USER, description="User role")
    permissions: list[str] = Field(default_factory=list, description="Additional permissions")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        return v
