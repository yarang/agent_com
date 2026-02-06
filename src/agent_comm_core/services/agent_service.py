"""
Agent service with business logic for Agent operations.

This service provides comprehensive business logic for managing AI agents,
including creation, retrieval, updating, deletion, and status management.
"""

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.models.common import AgentStatus
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase
from agent_comm_core.services.agent_api_key import AgentApiKeyService


class AgentRepository(SQLAlchemyRepositoryBase):
    """Repository for Agent database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, AgentDB)


class AgentService:
    """
    Service for managing AI agents with business logic.

    Provides operations for creating, retrieving, updating, and deleting agents,
    as well as managing agent status and API key generation.
    """

    # Valid status transitions for agents
    VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
        AgentStatus.OFFLINE.value: [
            AgentStatus.ONLINE.value,
            AgentStatus.ERROR.value,
        ],
        AgentStatus.ONLINE.value: [
            AgentStatus.OFFLINE.value,
            AgentStatus.BUSY.value,
            AgentStatus.ERROR.value,
        ],
        AgentStatus.BUSY.value: [
            AgentStatus.ONLINE.value,
            AgentStatus.OFFLINE.value,
            AgentStatus.ERROR.value,
        ],
        AgentStatus.ERROR.value: [
            AgentStatus.OFFLINE.value,
            AgentStatus.ONLINE.value,
        ],
    }

    def __init__(self, session: AsyncSession):
        """
        Initialize the agent service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._repository = AgentRepository(session)
        self._api_key_service = AgentApiKeyService(session)

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def create_agent(
        self,
        project_id: UUID,
        name: str,
        nickname: str | None = None,
        agent_type: str = "generic",
        capabilities: list[str] | None = None,
        config: dict | None = None,
        created_by_type: str = "user",
        created_by_id: UUID | None = None,
    ) -> AgentDB:
        """
        Create a new agent with validation.

        Args:
            project_id: Project UUID
            name: Agent name (unique per project)
            nickname: Optional display name
            agent_type: Type of agent (default: "generic")
            capabilities: List of agent capabilities
            config: Flexible configuration dictionary
            created_by_type: Type of creator (user/agent/system)
            created_by_id: ID of creator

        Returns:
            Created agent database model

        Raises:
            HTTPException: 409 if agent with same project_id and name exists
        """
        # Check for unique name per project
        existing = await self._session.execute(
            select(AgentDB).where(
                AgentDB.project_id == project_id,
                AgentDB.name == name,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"동일한 프로젝트 내에 '{name}' 이름의 에이전트가 이미 존재합니다.",
            )

        # Create agent with default status
        agent = AgentDB(
            id=uuid4(),
            project_id=project_id,
            name=name,
            nickname=nickname,
            agent_type=agent_type,
            status=AgentStatus.OFFLINE.value,
            capabilities=capabilities or [],
            config=config,
            is_active=True,
        )

        self._session.add(agent)
        await self._session.flush()

        # Generate API key for the new agent
        if created_by_id:
            await self._api_key_service.create_key(
                project_id=project_id,
                agent_id=agent.id,
                capabilities=capabilities or ["communicate"],
                created_by_type=created_by_type,
                created_by_id=created_by_id,
            )

        return agent

    async def get_agent(self, agent_id: UUID) -> AgentDB:
        """
        Get agent by ID.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent database model

        Raises:
            HTTPException: 404 if agent not found
        """
        agent = await self._repository.get_by_id(agent_id)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"에이전트를 찾을 수 없습니다: {agent_id}",
            )
        return agent

    async def list_agents(
        self,
        project_id: UUID | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentDB]:
        """
        List agents with filters and pagination.

        Args:
            project_id: Filter by project
            status: Filter by status
            is_active: Filter by active state
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of agent database models
        """
        filters = {}
        if project_id:
            filters["project_id"] = project_id
        if status:
            filters["status"] = status
        if is_active is not None:
            filters["is_active"] = is_active

        agents = await self._repository.list_all(
            limit=limit,
            offset=offset,
            order_by="created_at",
            descending=True,
            filters=filters if filters else None,
        )

        return list(agents)

    async def update_agent(
        self,
        agent_id: UUID,
        name: str | None = None,
        nickname: str | None = None,
        agent_type: str | None = None,
        capabilities: list[str] | None = None,
        config: dict | None = None,
        is_active: bool | None = None,
    ) -> AgentDB:
        """
        Update agent fields with partial update support.

        Args:
            agent_id: Agent UUID
            name: New name (optional)
            nickname: New nickname (optional)
            agent_type: New agent type (optional)
            capabilities: New capabilities list (optional)
            config: New configuration (optional)
            is_active: New active state (optional)

        Returns:
            Updated agent database model

        Raises:
            HTTPException: 404 if agent not found
            HTTPException: 409 if new name conflicts with existing agent
        """
        agent = await self.get_agent(agent_id)

        # Check for name conflict if name is being updated
        if name and name != agent.name:
            existing = await self._session.execute(
                select(AgentDB).where(
                    AgentDB.project_id == agent.project_id,
                    AgentDB.name == name,
                    AgentDB.id != agent_id,
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"동일한 프로젝트 내에 '{name}' 이름의 에이전트가 이미 존재합니다.",
                )
            agent.name = name

        # Update provided fields
        if nickname is not None:
            agent.nickname = nickname
        if agent_type is not None:
            agent.agent_type = agent_type
        if capabilities is not None:
            agent.capabilities = capabilities
        if config is not None:
            agent.config = config
        if is_active is not None:
            agent.is_active = is_active

        await self._session.flush()
        return agent

    async def delete_agent(self, agent_id: UUID) -> None:
        """
        Delete agent (CASCADE delete handled by DB).

        Args:
            agent_id: Agent UUID

        Raises:
            HTTPException: 404 if agent not found
        """
        agent = await self.get_agent(agent_id)
        await self._session.delete(agent)
        await self._session.flush()

    # ========================================================================
    # Status Management
    # ========================================================================

    async def update_agent_status(
        self,
        agent_id: UUID,
        new_status: str,
    ) -> AgentDB:
        """
        Update agent status with transition validation.

        Args:
            agent_id: Agent UUID
            new_status: New status value

        Returns:
            Updated agent database model

        Raises:
            HTTPException: 404 if agent not found
            HTTPException: 400 if status transition is invalid
        """
        agent = await self.get_agent(agent_id)

        # Validate status transition
        current_status = agent.status
        valid_transitions = self.VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"잘못된 상태 전환입니다: {current_status} -> {new_status}. "
                f"허용된 전환: {', '.join(valid_transitions)}",
            )

        # Update status and last_used timestamp
        agent.status = new_status

        # Update last_used timestamp via base class updated_at
        await self._session.flush()

        return agent

    async def set_agent_online(self, agent_id: UUID) -> AgentDB:
        """
        Set agent status to ONLINE.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent database model
        """
        return await self.update_agent_status(agent_id, AgentStatus.ONLINE.value)

    async def set_agent_offline(self, agent_id: UUID) -> AgentDB:
        """
        Set agent status to OFFLINE.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent database model
        """
        return await self.update_agent_status(agent_id, AgentStatus.OFFLINE.value)

    async def set_agent_busy(self, agent_id: UUID) -> AgentDB:
        """
        Set agent status to BUSY.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent database model
        """
        return await self.update_agent_status(agent_id, AgentStatus.BUSY.value)

    async def set_agent_error(self, agent_id: UUID) -> AgentDB:
        """
        Set agent status to ERROR.

        Args:
            agent_id: Agent UUID

        Returns:
            Updated agent database model
        """
        return await self.update_agent_status(agent_id, AgentStatus.ERROR.value)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    async def agent_exists(self, agent_id: UUID) -> bool:
        """
        Check if an agent exists.

        Args:
            agent_id: Agent UUID

        Returns:
            True if agent exists, False otherwise
        """
        return await self._repository.exists(agent_id)

    async def get_agents_by_ids(self, agent_ids: list[UUID]) -> list[AgentDB]:
        """
        Get multiple agents by their IDs.

        Args:
            agent_ids: List of agent UUIDs

        Returns:
            List of agent database models
        """
        return await self._repository.get_by_ids(agent_ids)

    async def count_agents(
        self,
        project_id: UUID | None = None,
        status: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """
        Count agents with optional filters.

        Args:
            project_id: Filter by project
            status: Filter by status
            is_active: Filter by active state

        Returns:
            Count of matching agents
        """
        filters = {}
        if project_id:
            filters["project_id"] = project_id
        if status:
            filters["status"] = status
        if is_active is not None:
            filters["is_active"] = is_active

        return await self._repository.count(filters if filters else None)

    async def get_online_agents(self, project_id: UUID) -> list[AgentDB]:
        """
        Get all online agents for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of online agent database models
        """
        return await self.list_agents(
            project_id=project_id,
            status=AgentStatus.ONLINE.value,
            is_active=True,
        )


def get_agent_service(session: AsyncSession) -> AgentService:
    """
    Get an agent service instance.

    Args:
        session: SQLAlchemy async session

    Returns:
        AgentService instance
    """
    return AgentService(session)
