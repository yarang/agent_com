"""
Database-backed authentication service for user and agent authentication.

Provides methods for authenticating dashboard users (JWT) and
agents (API tokens), with persistent storage in the database.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.config import get_config
from agent_comm_core.db.database import db_session
from agent_comm_core.db.models.agent_api_key import AgentApiKeyDB
from agent_comm_core.db.models.user import UserDB
from agent_comm_core.models.auth import Agent, User, UserRole
from agent_comm_core.repositories import AgentApiKeyRepository, UserRepository
from communication_server.security.tokens import (
    create_access_token,
    create_refresh_token,
    generate_agent_token,
    hash_api_token,
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


def _parse_permissions(permissions_str: str | None) -> list[str]:
    """Parse permissions from JSON string.

    Args:
        permissions_str: JSON string of permissions

    Returns:
        List of permissions
    """
    if not permissions_str:
        return []
    try:
        import json

        return json.loads(permissions_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _serialize_permissions(permissions: list[str] | None) -> str | None:
    """Serialize permissions to JSON string.

    Args:
        permissions: List of permissions

    Returns:
        JSON string or None
    """
    if not permissions:
        return None
    import json

    return json.dumps(permissions)


class AuthServiceDB:
    """
    Database-backed authentication service for users and agents.

    Handles JWT authentication for dashboard users and API token
    authentication for agents, with persistent database storage.
    """

    def __init__(self):
        """Initialize the authentication service."""
        # In-memory token blacklist for revocation (volatile by design)
        self._revoked_tokens: set[str] = set()
        # In-memory refresh token storage (volatile by design)
        self._refresh_tokens: dict[str, str] = {}

    async def _get_db_session(self) -> AsyncSession:
        """Get a database session.

        Returns:
            Async database session
        """
        # Use the context manager to get a session
        # Note: The caller is responsible for committing/closing
        from agent_comm_core.db.database import get_session_maker

        session_maker = get_session_maker()
        return session_maker()

    async def _initialize_admin_user(self) -> None:
        """
        Initialize default admin user if no users exist in database.

        The admin credentials should be changed immediately after first login.
        """
        async with db_session() as session:
            repo = UserRepository(session)

            # Check if any users exist
            existing_users = await repo.list_all(limit=1)
            try:
                _ = next(existing_users)
                # Users already exist, don't create admin
                return
            except StopIteration:
                # No users exist, create admin
                pass

            admin_username, admin_password = _get_admin_credentials()
            hashed_pw = self._hash_password(admin_password)

            await repo.create(
                username=admin_username,
                email=f"{admin_username}@localhost",  # Default email
                password_hash=hashed_pw,
                role=UserRole.ADMIN,
                permissions=["*"],
            )
            await session.commit()

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

    def _userdb_to_user(self, user_db: UserDB) -> User:
        """
        Convert UserDB to User model.

        Args:
            user_db: Database user model

        Returns:
            User model
        """
        return User(
            id=str(user_db.id),
            username=user_db.username,
            role=UserRole(user_db.role),
            permissions=_parse_permissions(user_db.permissions),
            is_active=user_db.is_active,
            created_at=user_db.created_at,
        )

    def _agentkeydb_to_agent(self, key_db: AgentApiKeyDB) -> Agent:
        """
        Convert AgentApiKeyDB to Agent model.

        Args:
            key_db: Database agent key model

        Returns:
            Agent model
        """
        return Agent(
            id=str(key_db.agent_id),
            project_id=str(key_db.project_id),
            nickname=key_db.key_id,  # Use key_id as nickname
            token=key_db.api_key_hash,
            capabilities=key_db.capabilities,
            is_active=key_db.is_active,
            created_at=key_db.created_at,
            last_used=key_db.updated_at,
        )

    async def authenticate_dashboard_user(self, username: str, password: str) -> User | None:
        """
        Authenticate a dashboard user with username and password.

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        async with db_session() as session:
            repo = UserRepository(session)
            user_db = await repo.get_by_username(username)

            if not user_db:
                return None

            if not user_db.is_active:
                return None

            if not self._verify_password(password, user_db.password_hash):
                return None

            return self._userdb_to_user(user_db)

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

            # Get user from database
            async with db_session() as session:
                repo = UserRepository(session)
                user_db = await repo.get_by_id(UUID(token_data.user_id))

                if not user_db:
                    return None

                if not user_db.is_active:
                    return None

                return self._userdb_to_user(user_db)

        except (JWTError, ValidationError, ValueError):
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

        # Hash the provided token to compare with stored hashes
        token_hash = hash_api_token(token)

        # Find agent by token hash in database
        async with db_session() as session:
            repo = AgentApiKeyRepository(session)
            key_db = await repo.get_by_hash(token_hash)

            if not key_db:
                return None

            if not key_db.is_active:
                return None

            # Update last used timestamp
            await repo.update_last_used(key_db.id)
            await session.commit()

            # MCP Broker fallback: Auto-register in AgentRegistry if not exists
            try:
                from communication_server.services.agent_registry import get_agent_registry

                registry = get_agent_registry()
                agent_id_str = str(key_db.agent_id)
                existing_agent = await registry.get_agent_by_full_id(agent_id_str)

                if existing_agent is None:
                    # Agent exists in database but not in AgentRegistry, register it
                    await registry.register_agent(
                        full_id=agent_id_str,
                        nickname=key_db.key_id,
                        capabilities=key_db.capabilities,
                        project_id=str(key_db.project_id),
                    )
            except Exception as e:
                # Log but don't fail authentication if registry fails
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to auto-register agent in AgentRegistry: {e}"
                )

            return self._agentkeydb_to_agent(key_db)

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
            project_id: Project ID (as string, will be converted to UUID)
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

        # Convert project_id to UUID
        try:
            project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
        except ValueError:
            # If project_id is not a valid UUID, create a new one
            project_uuid = uuid4()

        # Create agent ID
        agent_id = uuid4()

        # Generate key_id (human-readable identifier)
        key_id = f"{nickname}_{agent_id.hex[:8]}"

        # Store in database
        async with db_session() as session:
            repo = AgentApiKeyRepository(session)

            # Check if agent already exists in project
            existing = await repo.agent_exists_in_project(project_uuid, agent_id)

            if not existing:
                await repo.create(
                    project_id=project_uuid,
                    agent_id=agent_id,
                    key_id=key_id,
                    api_key_hash=hashed_token,
                    key_prefix=token[:20],  # Store first 20 chars as prefix
                    capabilities=capabilities,
                    created_by_type="user",
                    created_by_id=uuid4(),  # Default to system user
                )
                await session.commit()

        # Create Agent model
        agent = Agent(
            id=str(agent_id),
            project_id=str(project_uuid),
            nickname=nickname,
            token=hashed_token,
            capabilities=capabilities,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Auto-register in AgentRegistry for dashboard display
        try:
            from communication_server.services.agent_registry import get_agent_registry

            registry = get_agent_registry()
            await registry.register_agent(
                full_id=str(agent_id),
                nickname=nickname,
                capabilities=capabilities,
                project_id=str(project_uuid),
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
_auth_service_db: AuthServiceDB | None = None


def get_auth_service_db() -> AuthServiceDB:
    """
    Get the global database-backed authentication service instance.

    Returns:
        AuthServiceDB singleton instance
    """
    global _auth_service_db
    if _auth_service_db is None:
        _auth_service_db = AuthServiceDB()
    return _auth_service_db
