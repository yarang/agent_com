"""
Characterization tests for existing authentication behavior.

These tests capture the CURRENT behavior of the authentication system
to ensure backward compatibility during refactoring.
"""

import os
from datetime import UTC, datetime

import pytest

from agent_comm_core.models.auth import (
    Agent,
    User,
    UserRole,
)
from communication_server.security.auth import get_auth_service
from communication_server.security.tokens import (
    create_access_token,
    create_refresh_token,
    generate_agent_token,
    hash_api_token,
    validate_agent_token,
    verify_jwt_token,
)


class TestAuthTokenGenerationCharacterization:
    """Characterization tests for JWT token generation."""

    @pytest.fixture
    def mock_env_vars(self):
        """Set up required environment variables."""
        original = os.environ.get("JWT_SECRET_KEY")
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-min-32-chars-long"
        yield
        if original:
            os.environ["JWT_SECRET_KEY"] = original
        else:
            os.environ.pop("JWT_SECRET_KEY", None)

    def test_characterize_access_token_format(self, mock_env_vars):
        """Characterize: Access token format is JWT with 3 parts."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Document current behavior
        parts = token.split(".")
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}"

    def test_characterize_access_token_expiration_default(self, mock_env_vars):
        """Characterize: Default access token expiration is 15 minutes."""
        from jose import jwt

        data = {"sub": "user123"}
        token = create_access_token(data)

        # Decode to check expiration
        payload = jwt.decode(
            token,
            os.environ["JWT_SECRET_KEY"],
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
        )

        exp = datetime.fromtimestamp(payload["exp"], UTC)
        now = datetime.now(UTC)

        # Document current behavior: ~15 minutes
        delta_minutes = (exp - now).total_seconds() / 60
        assert 14 <= delta_minutes <= 16, f"Expected ~15 minutes, got {delta_minutes}"

    def test_characterize_refresh_token_format(self, mock_env_vars):
        """Characterize: Refresh token includes user_id and type='refresh'."""
        from jose import jwt

        token = create_refresh_token("user123")
        payload = jwt.decode(
            token,
            os.environ["JWT_SECRET_KEY"],
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
        )

        # Document current behavior
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"


class TestAgentTokenGenerationCharacterization:
    """Characterization tests for agent API token generation."""

    @pytest.fixture
    def mock_env_vars(self):
        """Set up required environment variables."""
        original = os.environ.get("API_TOKEN_SECRET")
        os.environ["API_TOKEN_SECRET"] = "test-api-token-secret-min-32-chars"
        yield
        if original:
            os.environ["API_TOKEN_SECRET"] = original
        else:
            os.environ.pop("API_TOKEN_SECRET", None)

    def test_characterize_agent_token_format(self, mock_env_vars):
        """Characterize: Agent token format is agent_{project_id}_{name}_{random}."""
        token = generate_agent_token("project1", "agent1")

        # Document current behavior
        assert token.startswith("agent_")
        assert "project1" in token
        assert "agent1" in token
        parts = token.split("_")
        assert len(parts) >= 3, f"Expected at least 3 parts, got {len(parts)}"

    def test_characterize_agent_token_hashing(self, mock_env_vars):
        """Characterize: Agent token hashing produces ~60 char hash (argon2)."""
        token = "test-api-token"
        hashed = hash_api_token(token)

        # Document current behavior
        assert isinstance(hashed, str)
        assert len(hashed) > 50  # argon2 produces variable length hash
        assert hashed != token

    def test_characterize_agent_token_validation(self, mock_env_vars):
        """Characterize: Token validation matches hashed token."""
        token = "test-api-token"
        hashed = hash_api_token(token)

        # Document current behavior
        assert validate_agent_token(token, hashed) is True
        assert validate_agent_token("wrong-token", hashed) is False


class TestAuthServiceCharacterization:
    """Characterization tests for AuthService behavior."""

    @pytest.fixture
    def auth_service(self):
        """Create auth service instance."""
        import communication_server.security.auth as auth_module

        auth_module._auth_service = None
        return get_auth_service()

    @pytest.mark.asyncio
    async def test_characterize_admin_user_initialized(self, auth_service):
        """Characterize: Admin user is auto-initialized with default credentials."""
        # Document current behavior
        assert "admin" in auth_service._users
        admin_data = auth_service._users["admin"]
        assert admin_data["role"] == "admin"
        assert admin_data["is_active"] is True
        assert "password_hash" in admin_data

    @pytest.mark.asyncio
    async def test_characterize_dashboard_user_auth_success(self, auth_service):
        """Characterize: Successful auth returns User with all fields populated."""
        user = await auth_service.authenticate_dashboard_user("admin", "change-me-immediately")

        # Document current behavior
        assert user is not None
        assert isinstance(user, User)
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
        assert user.is_active is True
        assert hasattr(user, "id")
        assert hasattr(user, "created_at")

    @pytest.mark.asyncio
    async def test_characterize_dashboard_user_auth_failure_wrong_password(self, auth_service):
        """Characterize: Wrong password returns None."""
        user = await auth_service.authenticate_dashboard_user("admin", "wrong-password")

        # Document current behavior
        assert user is None

    @pytest.mark.asyncio
    async def test_characterize_agent_token_creation(self, auth_service):
        """Characterize: Agent token creation returns token and Agent object."""
        token, agent = await auth_service.create_agent_token(
            project_id="project1",
            nickname="agent1",
            capabilities=["communicate"],
        )

        # Document current behavior
        assert isinstance(token, str)
        assert isinstance(agent, Agent)
        assert agent.nickname == "agent1"
        assert agent.project_id == "project1"
        assert agent.capabilities == ["communicate"]
        assert agent.is_active is True
        assert hasattr(agent, "id")
        assert hasattr(agent, "created_at")

    @pytest.mark.asyncio
    async def test_characterize_agent_authentication_valid_token(self, auth_service):
        """Characterize: Valid agent token returns authenticated Agent."""
        token, original_agent = await auth_service.create_agent_token(
            project_id="project1",
            nickname="agent1",
            capabilities=["communicate"],
        )

        authenticated_agent = await auth_service.authenticate_agent(token)

        # Document current behavior
        assert authenticated_agent is not None
        assert authenticated_agent.id == original_agent.id
        assert authenticated_agent.nickname == "agent1"

    @pytest.mark.asyncio
    async def test_characterize_agent_authentication_invalid_token(self, auth_service):
        """Characterize: Invalid agent token returns None."""
        agent = await auth_service.authenticate_agent("invalid-token")

        # Document current behavior
        assert agent is None

    @pytest.mark.asyncio
    async def test_characterize_user_tokens_creation(self, auth_service):
        """Characterize: User tokens creation returns dict with access, refresh, expires_in."""
        tokens = await auth_service.create_user_tokens("admin")

        # Document current behavior
        assert isinstance(tokens, dict)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_in" in tokens
        assert isinstance(tokens["access_token"], str)
        assert isinstance(tokens["refresh_token"], str)
        assert isinstance(tokens["expires_in"], int)


class TestTokenVerificationCharacterization:
    """Characterization tests for token verification."""

    @pytest.fixture
    def mock_env_vars(self):
        """Set up required environment variables."""
        original = os.environ.get("JWT_SECRET_KEY")
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-min-32-chars-long"
        yield
        if original:
            os.environ["JWT_SECRET_KEY"] = original
        else:
            os.environ.pop("JWT_SECRET_KEY", None)

    def test_characterize_jwt_verification_valid_token(self, mock_env_vars):
        """Characterize: Valid JWT token returns TokenData with user_id and type."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        token_data = verify_jwt_token(token)

        # Document current behavior
        assert token_data.user_id == "user123"
        assert token_data.type == "access"
        assert hasattr(token_data, "exp")

    def test_characterize_jwt_verification_expired_token_raises(self, mock_env_vars):
        """Characterize: Expired JWT token raises JWTError."""
        from jose import JWTError, jwt

        # Create expired token
        expired_payload = {
            "sub": "user123",
            "exp": (datetime.now(UTC).timestamp() - 3600),  # 1 hour ago
            "type": "access",
        }
        token = jwt.encode(
            expired_payload,
            os.environ["JWT_SECRET_KEY"],
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        )

        # Document current behavior
        with pytest.raises(JWTError):
            verify_jwt_token(token)
