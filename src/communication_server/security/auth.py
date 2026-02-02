"""
Authentication service for user and agent authentication.

Provides methods for authenticating dashboard users (JWT) and
agents (API tokens), as well as token management.
"""

from datetime import UTC, datetime

from jose import JWTError
from pydantic import ValidationError

from agent_comm_core.config import get_config
from agent_comm_core.models.auth import Agent, User
from communication_server.security.tokens import (
    create_access_token,
    create_refresh_token,
    generate_agent_token,
    hash_api_token,
    validate_agent_token,
    verify_jwt_token,
)

# Use argon2 for password hashing (more reliable than bcrypt)
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    HASHER = PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
    )
except ImportError:
    from passlib.context import CryptContext

    HASHER = CryptContext(
        schemes=["argon2"],
        deprecated="auto",
        argon2__time_cost=2,
        argon2__memory_cost=65536,
        argon2__parallelism=4,
    )


def _get_admin_credentials() -> tuple[str, str]:
    """Get admin credentials from config or environment.

    Returns:
        Tuple of (username, password)
    """
    import os

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "change-me-immediately")
    return username, password


class AuthService:
    """
    Authentication service for users and agents.

    Handles JWT authentication for dashboard users and API token
    authentication for agents.
    """

    def __init__(self):
        """Initialize the authentication service."""
        # In-memory user storage (replace with database in production)
        self._users: dict[str, dict] = {}
        # In-memory agent storage (replace with database in production)
        self._agents: dict[str, dict] = {}
        # In-memory token blacklist for revocation
        self._revoked_tokens: set[str] = set()
        # In-memory refresh token storage
        self._refresh_tokens: dict[str, str] = {}

        # Initialize default admin user if no users exist
        self._initialize_admin_user()

    def _initialize_admin_user(self) -> None:
        """
        Initialize default admin user on first startup.

        The admin credentials should be changed immediately after first login.
        """
        if not self._users:
            admin_username, admin_password = _get_admin_credentials()
            hashed_pw = self._hash_password(admin_password)
            self._users[admin_username] = {
                "id": "admin",
                "username": admin_username,
                "password_hash": hashed_pw,
                "role": "admin",
                "permissions": ["*"],
                "is_active": True,
                "created_at": datetime.now(UTC),
            }

    def _hash_password(self, password: str) -> str:
        """
        Hash a password using argon2.

        Args:
            password: Plain text password (must be at least 12 characters)

        Returns:
            Argon2 hashed password

        Raises:
            ValueError: If password is too short
        """
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")

        # Use argon2 PasswordHasher if available
        if hasattr(HASHER, "hash"):
            return HASHER.hash(password)
        else:
            # Fallback to passlib CryptContext
            return HASHER.hash(password)  # type: ignore[arg-type]

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Stored argon2 hash

        Returns:
            True if password matches hash, False otherwise
        """
        try:
            # Use argon2 PasswordHasher if available
            if hasattr(HASHER, "verify"):
                HASHER.verify(password_hash, password)
                return True
            else:
                # Fallback to passlib CryptContext
                return HASHER.verify(password, password_hash)  # type: ignore[arg-type]
        except (VerifyMismatchError, ValueError, TypeError):
            return False

    async def authenticate_dashboard_user(self, username: str, password: str) -> User | None:
        """
        Authenticate a dashboard user with username and password.

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user_data = self._users.get(username)
        if not user_data:
            return None

        if not user_data.get("is_active", True):
            return None

        if not self._verify_password(password, user_data["password_hash"]):
            return None

        # Create User object
        return User(
            id=user_data["id"],
            username=user_data["username"],
            role=user_data["role"],
            permissions=user_data.get("permissions", []),
            is_active=user_data.get("is_active", True),
            created_at=user_data.get("created_at", datetime.now(UTC)),
        )

    async def authenticate_user_with_token(self, token: str) -> User | None:
        """
        Authenticate a dashboard user using JWT token.

        Args:
            token: JWT access token

        Returns:
            User object if token is valid, None otherwise
        """
        try:
            # Check if token is revoked
            if token in self._revoked_tokens:
                return None

            # Verify token
            token_data = verify_jwt_token(token)

            if not token_data.user_id:
                return None

            # Get user
            user_data = self._users.get(token_data.user_id)
            if not user_data:
                return None

            if not user_data.get("is_active", True):
                return None

            return User(
                id=user_data["id"],
                username=user_data["username"],
                role=user_data["role"],
                permissions=user_data.get("permissions", []),
                is_active=user_data.get("is_active", True),
                created_at=user_data.get("created_at", datetime.now(UTC)),
            )

        except (JWTError, ValidationError):
            return None

    async def authenticate_agent(self, token: str) -> Agent | None:
        """
        Authenticate an agent using API token.

        Args:
            token: API bearer token

        Returns:
            Agent object if token is valid, None otherwise
        """
        # Check for token from config (for development)
        config = get_config()
        if config.authentication.api_token.value:
            if token == config.authentication.api_token.value:
                # Return a development agent
                return Agent(
                    id="dev-agent",
                    project_id=config.agent.project_id,
                    nickname=config.agent.nickname,
                    token="hashed",
                    capabilities=config.agent.capabilities,
                    is_active=True,
                    created_at=datetime.now(UTC),
                )

        # Find agent by token hash
        for agent_id, agent_data in self._agents.items():
            if validate_agent_token(token, agent_data["token"]):
                if not agent_data.get("is_active", True):
                    return None

                # Update last used timestamp
                agent_data["last_used"] = datetime.now(UTC)

                # MCP Broker fallback: Auto-register in AgentRegistry if not exists
                try:
                    from communication_server.services.agent_registry import get_agent_registry

                    registry = get_agent_registry()
                    existing_agent = await registry.get_agent_by_full_id(agent_id)

                    if existing_agent is None:
                        # Agent exists in AuthService but not in AgentRegistry, register it
                        await registry.register_agent(
                            full_id=agent_id,
                            nickname=agent_data["nickname"],
                            capabilities=agent_data.get("capabilities", []),
                            project_id=agent_data.get("project_id"),
                        )
                except Exception as e:
                    # Log but don't fail authentication if registry fails
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Failed to auto-register agent in AgentRegistry: {e}"
                    )

                return Agent(
                    id=agent_data["id"],
                    project_id=agent_data["project_id"],
                    nickname=agent_data["nickname"],
                    token=agent_data["token"],
                    capabilities=agent_data.get("capabilities", []),
                    is_active=agent_data.get("is_active", True),
                    created_at=agent_data.get("created_at", datetime.now(UTC)),
                    last_used=agent_data.get("last_used"),
                )

        return None

    async def create_user_tokens(self, user_id: str) -> dict:
        """
        Create access and refresh tokens for a user.

        Args:
            user_id: User ID to create tokens for

        Returns:
            Dictionary with access_token, refresh_token, and expires_in
        """
        config = get_config()
        access_token = create_access_token({"sub": user_id})
        refresh_token = create_refresh_token(user_id)

        # Store refresh token
        self._refresh_tokens[refresh_token] = user_id

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": config.authentication.jwt.access_token_expire_minutes * 60,
        }

    async def create_agent_token(
        self, project_id: str, nickname: str, capabilities: list[str]
    ) -> tuple[str, Agent]:
        """
        Create a new agent with API token.

        Args:
            project_id: Project ID
            nickname: Agent display name
            capabilities: List of agent capabilities

        Returns:
            Tuple of (plain_token, Agent object)

        Note:
            The plain token is only returned once. Store it securely.
        """
        # Generate token
        token = generate_agent_token(project_id, nickname)
        hashed_token = hash_api_token(token)

        # Create agent
        from uuid import uuid4

        agent_id = str(uuid4())
        agent = Agent(
            id=agent_id,
            project_id=project_id,
            nickname=nickname,
            token=hashed_token,
            capabilities=capabilities,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Store agent
        self._agents[agent_id] = {
            "id": agent.id,
            "project_id": agent.project_id,
            "nickname": agent.nickname,
            "token": agent.token,
            "capabilities": agent.capabilities,
            "is_active": agent.is_active,
            "created_at": agent.created_at,
            "last_used": None,
        }

        # Auto-register in AgentRegistry for dashboard display
        try:
            from communication_server.services.agent_registry import get_agent_registry

            registry = get_agent_registry()
            # Convert agent.id to string (Agent.id is UUID type)
            await registry.register_agent(
                full_id=str(agent.id),
                nickname=nickname,
                capabilities=capabilities,
                project_id=project_id,
            )
        except Exception as e:
            # Log but don't fail token creation if registry fails
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to auto-register agent in AgentRegistry: {e}"
            )

        return token, agent

    async def refresh_access_token(self, refresh_token: str) -> str | None:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        # Check if refresh token exists
        user_id = self._refresh_tokens.get(refresh_token)
        if not user_id:
            return None

        try:
            # Verify refresh token
            token_data = verify_jwt_token(refresh_token)

            if token_data.type != "refresh" or token_data.user_id != user_id:
                return None

            # Create new access token
            access_token = create_access_token({"sub": user_id})
            return access_token

        except JWTError:
            return None

    async def revoke_token(self, token: str, token_type: str = "access") -> bool:
        """
        Revoke a token by adding it to the blacklist.

        Args:
            token: Token to revoke
            token_type: Type of token ("access" or "refresh")

        Returns:
            True if token was revoked, False otherwise
        """
        if token_type == "refresh":
            # Remove refresh token
            if token in self._refresh_tokens:
                del self._refresh_tokens[token]
                return True
            return False

        # Add access token to blacklist
        self._revoked_tokens.add(token)
        return True

    async def logout(self, access_token: str, refresh_token: str) -> bool:
        """
        Logout a user by revoking both tokens.

        Args:
            access_token: Access token to revoke
            refresh_token: Refresh token to revoke

        Returns:
            True if logout was successful
        """
        await self.revoke_token(access_token, "access")
        await self.revoke_token(refresh_token, "refresh")
        return True


# Global auth service instance
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """
    Get the global authentication service instance.

    Returns:
        AuthService singleton instance
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
