"""
Agent API Key service with structured key format.

Implements the structured API key format: sk_agent_v1_{project_id}_{agent_id}_{hash}
"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_hex
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent_api_key import (
    AgentApiKeyDB,
    KeyStatus,
)
from agent_comm_core.models.agent_api_key import (
    AgentApiKeyResponse,
    AgentKeyValidationResult,
)


class AgentApiKeyService:
    """Service for managing agent API keys with structured format."""

    def __init__(self, session: AsyncSession):
        """Initialize the API key service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    @staticmethod
    def generate_structured_key(project_id: UUID, agent_id: UUID) -> tuple[str, str]:
        """Generate a structured API key and its hash.

        Format: sk_agent_v1_{project_id_short}_{agent_id}_{hash}

        Args:
            project_id: Project UUID
            agent_id: Agent UUID

        Returns:
            Tuple of (plain_key, key_hash)
        """
        # Shorten project_id to first 8 chars
        project_short = str(project_id)[:8]

        # Generate random hash component (8 characters)
        hash_component = token_hex(4)

        # Construct the structured key
        plain_key = f"sk_agent_v1_{project_short}_{agent_id}_{hash_component}"

        # SHA-256 hash for storage
        key_hash = sha256(plain_key.encode()).hexdigest()

        return plain_key, key_hash

    @staticmethod
    def parse_structured_key(key: str) -> dict | None:
        """Parse a structured API key to extract components.

        Args:
            key: The API key to parse

        Returns:
            Dictionary with components or None if invalid
        """
        parts = key.split("_")

        if len(parts) < 6:
            return None

        # Format: sk_agent_v1_{project_id_short}_{agent_id}_{hash}
        if parts[0] != "sk" or parts[1] != "agent" or parts[2] != "v1":
            return None

        return {
            "project_id_short": parts[3],
            "agent_id": parts[4],
            "hash": parts[5] if len(parts) > 5 else None,
        }

    async def create_key(
        self,
        project_id: UUID,
        agent_id: UUID,
        capabilities: list[str],
        created_by_type: str,
        created_by_id: UUID,
        expires_in_days: int | None = None,
    ) -> AgentApiKeyResponse:
        """Create a new agent API key.

        Args:
            project_id: Project UUID
            agent_id: Agent UUID
            capabilities: List of capabilities
            created_by_type: Type of creator (user/agent/system)
            created_by_id: ID of creator
            expires_in_days: Optional expiration in days

        Returns:
            Created API key response (plain key only shown once)

        Raises:
            HTTPException: If key already exists for this agent/project
        """
        # Check if key already exists
        existing = await self._session.execute(
            select(AgentApiKeyDB).where(
                AgentApiKeyDB.project_id == project_id,
                AgentApiKeyDB.agent_id == agent_id,
                AgentApiKeyDB.status == KeyStatus.ACTIVE,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active API key already exists for this agent in this project",
            )

        # Generate structured key
        plain_key, key_hash = self.generate_structured_key(project_id, agent_id)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        # Create key ID (human-readable)
        key_id = f"key_{agent_id.hex[:8]}_{datetime.now(UTC).strftime('%Y%m%d')}"

        # Create database record
        key_record = AgentApiKeyDB(
            project_id=project_id,
            agent_id=agent_id,
            key_id=key_id,
            api_key_hash=key_hash,
            key_prefix=plain_key[:20],  # Store prefix for identification
            capabilities=capabilities,
            status=KeyStatus.ACTIVE,
            expires_at=expires_at,
            created_by_type=created_by_type,
            created_by_id=created_by_id,
        )

        self._session.add(key_record)
        await self._session.flush()

        return AgentApiKeyResponse(
            id=key_record.id,
            key_id=key_record.key_id,
            agent_id=key_record.agent_id,
            project_id=key_record.project_id,
            capabilities=key_record.capabilities,
            key_prefix=key_record.key_prefix,
            status=key_record.status,
            expires_at=key_record.expires_at,
            created_at=key_record.created_at,
            plain_key=plain_key,  # Only shown on creation
        )

    async def validate_key(self, key: str) -> AgentKeyValidationResult | None:
        """Validate an agent API key.

        Args:
            key: The API key to validate

        Returns:
            Validation result with key details if valid, None otherwise
        """
        # Parse structured key
        parsed = self.parse_structured_key(key)
        if not parsed:
            return None

        # Hash the key and look it up
        key_hash = sha256(key.encode()).hexdigest()

        # Query database
        result = await self._session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.api_key_hash == key_hash)
        )
        key_record = result.scalar_one_or_none()

        if not key_record:
            return None

        # Check if key is active
        if not key_record.is_active:
            return AgentKeyValidationResult(
                valid=False,
                reason=f"Key is {key_record.status}",
                agent_id=None,
                project_id=None,
                capabilities=[],
            )

        return AgentKeyValidationResult(
            valid=True,
            reason="Valid",
            agent_id=key_record.agent_id,
            project_id=key_record.project_id,
            capabilities=key_record.capabilities,
        )

    async def revoke_key(self, key_id: str, revoked_by_id: UUID) -> bool:
        """Revoke an API key.

        Args:
            key_id: The key ID to revoke
            revoked_by_id: ID of user revoking the key

        Returns:
            True if revoked, False if not found
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.key_id == key_id)
        )
        key_record = result.scalar_one_or_none()

        if not key_record:
            return False

        key_record.status = KeyStatus.REVOKED
        await self._session.flush()

        return True

    async def revoke_all_agent_keys(self, agent_id: UUID) -> int:
        """Revoke all keys for an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Number of keys revoked
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(
                AgentApiKeyDB.agent_id == agent_id,
                AgentApiKeyDB.status == KeyStatus.ACTIVE,
            )
        )
        keys = result.scalars().all()

        count = 0
        for key in keys:
            key.status = KeyStatus.REVOKED
            count += 1

        await self._session.flush()
        return count

    async def revoke_all_project_keys(self, project_id: UUID) -> int:
        """Revoke all keys for a project (panic mode).

        Args:
            project_id: Project UUID

        Returns:
            Number of keys revoked
        """
        result = await self._session.execute(
            select(AgentApiKeyDB).where(
                AgentApiKeyDB.project_id == project_id,
                AgentApiKeyDB.status == KeyStatus.ACTIVE,
            )
        )
        keys = result.scalars().all()

        count = 0
        for key in keys:
            key.status = KeyStatus.REVOKED
            count += 1

        await self._session.flush()
        return count

    async def list_keys(
        self, project_id: UUID | None = None, agent_id: UUID | None = None
    ) -> list[AgentApiKeyResponse]:
        """List API keys with optional filtering.

        Args:
            project_id: Optional project filter
            agent_id: Optional agent filter

        Returns:
            List of API key responses (without plain keys)
        """
        stmt = select(AgentApiKeyDB)

        if project_id:
            stmt = stmt.where(AgentApiKeyDB.project_id == project_id)
        if agent_id:
            stmt = stmt.where(AgentApiKeyDB.agent_id == agent_id)

        result = await self._session.execute(stmt.order_by(AgentApiKeyDB.created_at.desc()))
        keys = result.scalars().all()

        return [
            AgentApiKeyResponse(
                id=key.id,
                key_id=key.key_id,
                agent_id=key.agent_id,
                project_id=key.project_id,
                capabilities=key.capabilities,
                key_prefix=key.key_prefix,
                status=key.status,
                expires_at=key.expires_at,
                created_at=key.created_at,
                plain_key=None,  # Never include plain key in list
            )
            for key in keys
        ]


def get_agent_api_key_service(session: AsyncSession) -> AgentApiKeyService:
    """Get an agent API key service instance.

    Args:
        session: SQLAlchemy async session

    Returns:
        AgentApiKeyService instance
    """
    return AgentApiKeyService(session)
