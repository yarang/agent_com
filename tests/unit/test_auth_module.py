"""
Unit tests for the security authentication module.

Tests JWT tokens, API tokens, authentication service, and middleware.
"""

import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from agent_comm_core.models.auth import (
    Agent,
    AgentTokenCreate,
    LoginRequest,
    Token,
    TokenData,
    User,
    UserRole,
)

from communication_server.security.auth import AuthService, get_auth_service
from communication_server.security.tokens import (
    TokenData,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_jwt_token,
    generate_agent_token,
    hash_api_token,
    validate_agent_token,
    extract_token_from_header,
)
from communication_server.security.dependencies import (
    get_current_user,
    get_current_agent,
    require_agent,
)
from communication_server.security.middleware import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)


# ============================================================================
# Token Management Tests
# ============================================================================


class TestTokenManagement:
    """Test token generation and validation."""

    @pytest.fixture
    def mock_env_vars(self):
        """Set up required environment variables."""
        original_vals = {
            "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
            "API_TOKEN_SECRET": os.environ.get("API_TOKEN_SECRET"),
        }
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-min-32-chars-long"
        os.environ["API_TOKEN_SECRET"] = "test-api-token-secret-min-32-chars"
        yield
        for k, v in original_vals.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_create_access_token(self, mock_env_vars):
        """Test JWT access token creation."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token structure
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    def test_create_access_token_custom_expiration(self, mock_env_vars):
        """Test JWT access token with custom expiration."""
        data = {"sub": "user123"}
        token = create_access_token(data, expires_delta=30)

        assert token is not None

        # Decode and check expiration
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp > now + timedelta(minutes=29)
        assert exp < now + timedelta(minutes=31)

    def test_create_refresh_token(self, mock_env_vars):
        """Test refresh token creation."""
        token = create_refresh_token("user123")

        assert token is not None
        assert isinstance(token, str)

        # Verify payload
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_jwt_token_valid(self, mock_env_vars):
        """Test verification of valid JWT token."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        token_data = verify_jwt_token(token)
        assert token_data.user_id == "user123"
        assert token_data.type == "access"

    def test_verify_jwt_token_expired(self, mock_env_vars):
        """Test verification of expired JWT token."""
        # Create expired token
        from jose import jwt

        expired_payload = {
            "sub": "user123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(
            expired_payload,
            os.environ["JWT_SECRET_KEY"],
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        )

        with pytest.raises(Exception):  # JWTError
            verify_jwt_token(token)

    def test_generate_agent_token(self, mock_env_vars):
        """Test agent API token generation."""
        token = generate_agent_token("project1", "agent1")

        assert token is not None
        assert isinstance(token, str)
        assert token.startswith("agent_")
        assert "project1" in token
        assert "agent1" in token

    def test_hash_api_token(self, mock_env_vars):
        """Test API token hashing."""
        token = "test-api-token"
        hashed = hash_api_token(token)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) == 60  # bcrypt hash length
        assert hashed != token

    def test_validate_agent_token_valid(self, mock_env_vars):
        """Test validation of valid agent token."""
        token = "test-api-token"
        hashed = hash_api_token(token)

        assert validate_agent_token(token, hashed) is True

    def test_validate_agent_token_invalid(self, mock_env_vars):
        """Test validation of invalid agent token."""
        token = "test-api-token"
        hashed = hash_api_token(token)

        assert validate_agent_token("wrong-token", hashed) is False

    def test_extract_token_from_header_valid(self):
        """Test extraction of token from valid Authorization header."""
        header = "Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
        token = extract_token_from_header(header)

        assert token == "eyJ0eXAiOiJKV1QiLCJhbGc..."

    def test_extract_token_from_header_invalid(self):
        """Test extraction from invalid Authorization header."""
        with pytest.raises(ValueError):
            extract_token_from_header("InvalidFormat")

        with pytest.raises(ValueError):
            extract_token_from_header("")

    def test_create_access_token_requires_secret_key(self):
        """Test that access token creation requires JWT_SECRET_KEY."""
        original = os.environ.get("JWT_SECRET_KEY")
        os.environ.pop("JWT_SECRET_KEY", None)

        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            create_access_token({"sub": "user"})

        if original:
            os.environ["JWT_SECRET_KEY"] = original


# ============================================================================
# Auth Service Tests
# ============================================================================


class TestAuthService:
    """Test authentication service."""

    @pytest.fixture
    def auth_service(self):
        """Create auth service instance."""
        # Reset global service
        import communication_server.security.auth as auth_module

        auth_module._auth_service = None
        return get_auth_service()

    @pytest.mark.asyncio
    async def test_authenticate_dashboard_user_success(self, auth_service):
        """Test successful dashboard user authentication."""
        # Create admin user
        user = await auth_service.authenticate_dashboard_user("admin", "change-me-immediately")

        assert user is not None
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_authenticate_dashboard_user_invalid_password(self, auth_service):
        """Test authentication with invalid password."""
        user = await auth_service.authenticate_dashboard_user("admin", "wrong-password")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_dashboard_user_invalid_username(self, auth_service):
        """Test authentication with invalid username."""
        user = await auth_service.authenticate_dashboard_user("nonexistent", "password")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_with_token_valid(self, auth_service):
        """Test user authentication with valid JWT token."""
        # First, get tokens
        tokens = await auth_service.create_user_tokens("admin")

        # Authenticate with token
        user = await auth_service.authenticate_user_with_token(tokens["access_token"])

        assert user is not None
        assert user.username == "admin"

    @pytest.mark.asyncio
    async def test_authenticate_agent_token_valid(self, auth_service):
        """Test agent authentication with valid API token."""
        token, agent = await auth_service.create_agent_token(
            project_id="project1",
            nickname="agent1",
            capabilities=["communicate"],
        )

        authenticated_agent = await auth_service.authenticate_agent(token)

        assert authenticated_agent is not None
        assert authenticated_agent.id == agent.id
        assert authenticated_agent.nickname == "agent1"
        assert authenticated_agent.can_communicate is True

    @pytest.mark.asyncio
    async def test_create_user_tokens(self, auth_service):
        """Test user token creation."""
        tokens = await auth_service.create_user_tokens("admin")

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_in" in tokens
        assert tokens["expires_in"] == 15 * 60  # 15 minutes

    @pytest.mark.asyncio
    async def test_refresh_access_token_valid(self, auth_service):
        """Test access token refresh with valid refresh token."""
        tokens = await auth_service.create_user_tokens("admin")

        new_access_token = await auth_service.refresh_access_token(tokens["refresh_token"])

        assert new_access_token is not None
        assert new_access_token != tokens["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid(self, auth_service):
        """Test access token refresh with invalid refresh token."""
        new_access_token = await auth_service.refresh_access_token("invalid-token")

        assert new_access_token is None

    @pytest.mark.asyncio
    async def test_revoke_token_access(self, auth_service):
        """Test revoking an access token."""
        tokens = await auth_service.create_user_tokens("admin")

        # Revoke token
        result = await auth_service.revoke_token(tokens["access_token"], "access")
        assert result is True

        # Try to authenticate with revoked token
        user = await auth_service.authenticate_user_with_token(tokens["access_token"])
        assert user is None

    @pytest.mark.asyncio
    async def test_logout(self, auth_service):
        """Test user logout."""
        tokens = await auth_service.create_user_tokens("admin")

        result = await auth_service.logout(tokens["access_token"], tokens["refresh_token"])
        assert result is True

        # Verify tokens are revoked
        user = await auth_service.authenticate_user_with_token(tokens["access_token"])
        assert user is None


# ============================================================================
# Dependencies Tests
# ============================================================================


class TestDependencies:
    """Test FastAPI authentication dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        # Mock credentials
        mock_creds = MagicMock(spec=HTTPAuthorizationCredentials)
        mock_creds.credentials = "valid-token"

        with patch(
            "communication_server.security.dependencies.get_auth_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_user = User(id="user1", username="admin", role=UserRole.ADMIN)
            mock_service.authenticate_user_with_token.return_value = mock_user
            mock_get_service.return_value = mock_service

            user = await get_current_user(mock_creds)
            assert user is not None
            assert user.username == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        with patch("communication_server.security.dependencies.get_auth_service"):
            with pytest.raises(HTTPException, match="Not authenticated"):
                await get_current_user(None)

    @pytest.mark.asyncio
    async def test_get_current_agent_valid_token(self):
        """Test getting current agent with valid token."""
        with patch(
            "communication_server.security.dependencies.get_auth_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_agent = Agent(
                id=uuid4(),
                project_id="project1",
                nickname="agent1",
                token="hashed_token",
                capabilities=["communicate"],
            )
            mock_service.authenticate_agent.return_value = mock_agent
            mock_get_service.return_value = mock_service

            agent = await get_current_agent("Bearer valid-token")
            assert agent is not None
            assert agent.nickname == "agent1"


# ============================================================================
# Middleware Tests
# ============================================================================


class TestAuthenticationMiddleware:
    """Test authentication middleware."""

    @pytest.mark.asyncio
    async def test_middleware_adds_user_to_state(self):
        """Test that middleware adds authenticated user to request state."""
        app = MagicMock()
        middleware = AuthenticationMiddleware(app, require_auth=False)

        # Mock request
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer valid-token"}
        request.state = MagicMock()

        # Mock service
        with patch("communication_server.security.middleware.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_user = User(id="user1", username="admin", role=UserRole.ADMIN)
            mock_service.authenticate_user_with_token.return_value = mock_user
            mock_service.authenticate_agent.return_value = None
            mock_get_service.return_value = mock_service

            # Mock call_next
            response = MagicMock(spec=Response)
            call_next = AsyncMock(return_value=response)

            result = await middleware(request, call_next)

            assert hasattr(request.state, "user")
            assert request.state.user.username == "admin"
            call_next.assert_called_once_with(request)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    @pytest.mark.asyncio
    async def test_middleware_adds_security_headers(self):
        """Test that middleware adds security headers."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)

        # Mock request and response
        request = MagicMock(spec=Request)
        response = MagicMock(spec=Response)
        response.headers = {}

        call_next = AsyncMock(return_value=response)

        result = await middleware(request, call_next)

        # Verify headers
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in result.headers


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        app = MagicMock()
        middleware = RateLimitMiddleware(app, requests_per_minute=60)

        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock(spec=Response)
        call_next = AsyncMock(return_value=response)

        # Make 10 requests
        for _ in range(10):
            result = await middleware(request, call_next)
            assert result is not None

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        app = MagicMock()
        middleware = RateLimitMiddleware(app, requests_per_minute=5)

        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        response = MagicMock(spec=Response)
        call_next = AsyncMock(return_value=response)

        # Make 5 requests (at limit)
        for _ in range(5):
            await middleware(request, call_next)

        # 6th request should be blocked
        with pytest.raises(HTTPException, match="Rate limit exceeded"):
            await middleware(request, call_next)


# ============================================================================
# Model Tests
# ============================================================================


class TestAuthModels:
    """Test authentication models."""

    def test_user_model_admin_role(self):
        """Test User model with admin role."""
        user = User(
            id="user1",
            username="admin",
            role=UserRole.ADMIN,
            permissions=["*"],
        )

        assert user.is_admin is True
        assert user.can_write is True

    def test_user_model_readonly_role(self):
        """Test User model with readonly role."""
        user = User(
            id="user1",
            username="readonly",
            role=UserRole.READONLY,
            permissions=[],
        )

        assert user.is_admin is False
        assert user.can_write is False

    def test_agent_model_capabilities(self):
        """Test Agent model with capabilities."""
        agent = Agent(
            id=uuid4(),
            project_id="project1",
            nickname="agent1",
            token="hashed_token",
            capabilities=["communicate", "create_meetings"],
        )

        assert agent.can_communicate is True
        assert agent.can_create_meetings is True

    def test_agent_model_inactive(self):
        """Test inactive agent cannot communicate."""
        agent = Agent(
            id=uuid4(),
            project_id="project1",
            nickname="agent1",
            token="hashed_token",
            capabilities=["communicate"],
            is_active=False,
        )

        assert agent.can_communicate is False

    def test_login_request_validation(self):
        """Test LoginRequest model validation."""
        # Valid request
        request = LoginRequest(
            username="admin",
            password="twelve-chars!",
        )
        assert request.username == "admin"
        assert request.password == "twelve-chars!"
