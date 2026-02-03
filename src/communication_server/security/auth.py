"""
Authentication service for user and agent authentication.

Provides methods for authenticating dashboard users (JWT) and
agents (API tokens), as well as token management.

This service now uses database storage for persistence across
server restarts.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from jose import JWTError
from pydantic import ValidationError

from agent_comm_core.config import get_config
from agent_comm_core.db.database import db_session
from agent_comm_core.db.models.user import UserDB
from agent_comm_core.models.auth import Agent, User, UserRole
from agent_comm_core.repositories import UserRepository
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


def _parse_project_uuid(project_id: str) -> UUID:
    """Parse project ID as UUID, returning new UUID if invalid.

    Args:
        project_id: Project ID string

    Returns:
        Parsed UUID or new UUID if invalid
    """
    if project_id == "default":
        return uuid4()
    try:
        return UUID(project_id)
    except ValueError:
        return uuid4()


class AuthService:
    """
    Authentication service for users and agents.

    Handles JWT authentication for dashboard users and API token
    authentication for agents. Uses database storage for persistence.
    """

    def __init__(self):
        """Initialize the authentication service."""
        # In-memory token blacklist for revocation (volatile by design)
        self._revoked_tokens: set[str] = set()
        # In-memory refresh token storage (volatile by design)
        self._refresh_tokens: dict[str, str] = {}

        # Note: Users and agents are now stored in the database
        # We don't initialize admin here to avoid database access in __init__

    async def _initialize_admin_user(self) -> None:
        """
        Initialize default admin user on first startup.

        The admin credentials should be changed immediately after first login.
        This method is idempotent - it only creates the admin user if no users exist.
        """
        import json

        from sqlalchemy.exc import IntegrityError

        async with db_session() as session:
            repo = UserRepository(session)

            # Check if admin user already exists
            admin_username, _ = _get_admin_credentials()
            existing_admin = await repo.get_by_username(admin_username)
            if existing_admin is not None:
                # Admin already exists, nothing to do
                return

            # Check if any users exist (only create admin if no users exist)
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

            try:
                await repo.create(
                    username=admin_username,
                    email=f"{admin_username}@localhost",  # Default email
                    password_hash=hashed_pw,
                    role=UserRole.ADMIN,
                    permissions=json.dumps(["*"]),  # Store as JSON string
                )
                await session.commit()
            except IntegrityError:
                # Admin was created concurrently (race condition)
                # This is fine, just rollback and continue
                await session.rollback()

    async def _ensure_admin_exists(self) -> None:
        """Ensure admin user exists, creating if necessary."""
        await self._initialize_admin_user()

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
        # Ensure admin user exists for initial login
        await self._ensure_admin_exists()

        async with db_session() as session:
            repo = UserRepository(session)
            user_db = await repo.get_by_username(username)

            if not user_db:
                return None

            if not user_db.is_active:
                return None

            if not self._verify_password(password, user_db.password_hash):
                return None

            # Convert UserDB to User model
            return User(
                id=str(user_db.id),
                username=user_db.username,
                role=UserRole(user_db.role),
                permissions=_parse_permissions(user_db.permissions),
                is_active=user_db.is_active,
                created_at=user_db.created_at,
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

            # Get user from database
            async with db_session() as session:
                repo = UserRepository(session)

                # Convert user_id string to UUID
                from uuid import UUID

                user_db = await repo.get_by_id(UUID(token_data.user_id))

                if not user_db:
                    return None

                if not user_db.is_active:
                    return None

                return User(
                    id=str(user_db.id),
                    username=user_db.username,
                    role=UserRole(user_db.role),
                    permissions=_parse_permissions(user_db.permissions),
                    is_active=user_db.is_active,
                    created_at=user_db.created_at,
                )

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
        dev_token = config.authentication.api_token.value
        if dev_token and token == dev_token:
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

        # Find agent by token hash in database
        # Hash the provided token to compare with stored hashes
        token_hash = hash_api_token(token)

        async with db_session() as session:
            from agent_comm_core.repositories import AgentApiKeyRepository

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

            return Agent(
                id=str(key_db.agent_id),
                project_id=str(key_db.project_id),
                nickname=key_db.key_id,
                token=key_db.api_key_hash,
                capabilities=key_db.capabilities,
                is_active=key_db.is_active,
                created_at=key_db.created_at,
                last_used=key_db.updated_at,
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
            project_id: Project ID (as string, will be converted to UUID)
            nickname: Agent display name
            capabilities: List of agent capabilities

        Returns:
            Tuple of (plain_token, Agent object)

        Note:
            The plain token is only returned once. Store it securely.
        """
        from agent_comm_core.db.models.project import ProjectDB
        from agent_comm_core.repositories import AgentApiKeyRepository

        # Generate token
        token = generate_agent_token(project_id, nickname)
        hashed_token = hash_api_token(token)

        # Create agent ID
        agent_id = uuid4()

        # Convert project_id to UUID (create default project if needed)
        project_uuid = _parse_project_uuid(project_id)

        # Generate key_id (human-readable identifier)
        key_id = f"{nickname}_{agent_id.hex[:8]}"

        # Store in database
        async with db_session() as session:
            # Check if project exists, if not create a default one
            from sqlalchemy import select

            project_result = await session.execute(
                select(ProjectDB).where(ProjectDB.id == project_uuid)
            )
            project_db = project_result.scalar_one_or_none()

            if not project_db:
                # Create a default project for the agent
                # We need a user_id for the project, use a system user
                default_user = await session.execute(
                    select(UserDB).where(UserDB.username == "admin")
                )
                user_db = default_user.scalar_one_or_none()

                if not user_db:
                    # No admin user exists, create a default one for system agents
                    # This allows agent token creation to work in fresh installations
                    import json

                    user_db = UserDB(
                        username="admin",
                        email="admin@localhost",
                        password_hash=self._hash_password(
                            "DefaultPassword123!"
                        ),  # User should change this
                        role=UserRole.ADMIN.value,
                        permissions=json.dumps(["*"]),  # Store as JSON string
                    )
                    session.add(user_db)
                    await session.flush()

                project_db = ProjectDB(
                    id=project_uuid,
                    owner_id=user_db.id,
                    project_id=f"project_{project_uuid.hex[:8]}",
                    name=f"Default Project for {nickname}",
                    status="active",
                )
                session.add(project_db)
                await session.flush()

            repo = AgentApiKeyRepository(session)

            # Create the agent API key
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
