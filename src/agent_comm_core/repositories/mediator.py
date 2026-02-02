"""
Mediator system repository.

Provides database access for mediator models, prompts, and assignments.
"""

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.mediator import (
    ChatRoomMediatorDB,
    MediatorDB,
    MediatorModelDB,
    MediatorPromptDB,
)
from agent_comm_core.models.mediator import (
    ChatRoomMediatorCreate,
    ChatRoomMediatorUpdate,
    MediatorCreate,
    MediatorModelCreate,
    MediatorModelUpdate,
    MediatorPromptCreate,
    MediatorPromptUpdate,
    MediatorUpdate,
)


class MediatorRepository:
    """
    Repository for mediator data access.

    Provides methods for CRUD operations on mediators,
    mediator models, and mediator prompts.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    # ========================================================================
    # Mediator Model Operations
    # ========================================================================

    async def create_model(self, data: MediatorModelCreate) -> MediatorModelDB:
        """
        Create a new mediator model.

        Args:
            data: Model creation data

        Returns:
            Created model
        """
        model = MediatorModelDB(**data.model_dump())
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_model(self, model_id: UUID) -> MediatorModelDB | None:
        """
        Get a mediator model by ID.

        Args:
            model_id: Model ID

        Returns:
            Model or None if not found
        """
        result = await self.session.execute(
            select(MediatorModelDB).where(MediatorModelDB.id == model_id)
        )
        return result.scalar_one_or_none()

    async def get_model_by_name(self, name: str) -> MediatorModelDB | None:
        """
        Get a mediator model by name.

        Args:
            name: Model name

        Returns:
            Model or None if not found
        """
        result = await self.session.execute(
            select(MediatorModelDB).where(MediatorModelDB.name == name)
        )
        return result.scalar_one_or_none()

    async def list_models(
        self, provider: str | None = None, is_active: bool | None = None
    ) -> list[MediatorModelDB]:
        """
        List mediator models with optional filtering.

        Args:
            provider: Filter by provider
            is_active: Filter by active status

        Returns:
            List of models
        """
        query = select(MediatorModelDB)

        if provider:
            query = query.where(MediatorModelDB.provider == provider)
        if is_active is not None:
            query = query.where(MediatorModelDB.is_active == is_active)

        query = query.order_by(MediatorModelDB.name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_model(
        self, model_id: UUID, data: MediatorModelUpdate
    ) -> MediatorModelDB | None:
        """
        Update a mediator model.

        Args:
            model_id: Model ID
            data: Update data

        Returns:
            Updated model or None if not found
        """
        update_data = data.model_dump(exclude_unset=True)

        result = await self.session.execute(
            update(MediatorModelDB)
            .where(MediatorModelDB.id == model_id)
            .values(**update_data)
            .returning(MediatorModelDB)
        )

        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_model(self, model_id: UUID) -> bool:
        """
        Delete a mediator model.

        Args:
            model_id: Model ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(MediatorModelDB).where(MediatorModelDB.id == model_id)
        )
        await self.session.flush()
        return result.rowcount > 0

    # ========================================================================
    # Mediator Prompt Operations
    # ========================================================================

    async def create_prompt(self, data: MediatorPromptCreate) -> MediatorPromptDB:
        """
        Create a new mediator prompt.

        Args:
            data: Prompt creation data

        Returns:
            Created prompt
        """
        prompt = MediatorPromptDB(**data.model_dump())
        self.session.add(prompt)
        await self.session.flush()
        return prompt

    async def get_prompt(self, prompt_id: UUID) -> MediatorPromptDB | None:
        """
        Get a mediator prompt by ID.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt or None if not found
        """
        result = await self.session.execute(
            select(MediatorPromptDB).where(MediatorPromptDB.id == prompt_id)
        )
        return result.scalar_one_or_none()

    async def list_prompts(
        self,
        project_id: UUID,
        category: str | None = None,
        is_public: bool | None = None,
        is_active: bool | None = None,
    ) -> list[MediatorPromptDB]:
        """
        List mediator prompts with optional filtering.

        Args:
            project_id: Project ID
            category: Filter by category
            is_public: Filter by public status
            is_active: Filter by active status

        Returns:
            List of prompts
        """
        query = select(MediatorPromptDB).where(MediatorPromptDB.project_id == project_id)

        if category:
            query = query.where(MediatorPromptDB.category == category)
        if is_public is not None:
            query = query.where(MediatorPromptDB.is_public == is_public)
        if is_active is not None:
            query = query.where(MediatorPromptDB.is_active == is_active)

        query = query.order_by(MediatorPromptDB.name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_prompt(
        self, prompt_id: UUID, data: MediatorPromptUpdate
    ) -> MediatorPromptDB | None:
        """
        Update a mediator prompt.

        Args:
            prompt_id: Prompt ID
            data: Update data

        Returns:
            Updated prompt or None if not found
        """
        update_data = data.model_dump(exclude_unset=True)

        result = await self.session.execute(
            update(MediatorPromptDB)
            .where(MediatorPromptDB.id == prompt_id)
            .values(**update_data)
            .returning(MediatorPromptDB)
        )

        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_prompt(self, prompt_id: UUID) -> bool:
        """
        Delete a mediator prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(MediatorPromptDB).where(MediatorPromptDB.id == prompt_id)
        )
        await self.session.flush()
        return result.rowcount > 0

    # ========================================================================
    # Mediator Operations
    # ========================================================================

    async def create_mediator(self, data: MediatorCreate) -> MediatorDB:
        """
        Create a new mediator.

        Args:
            data: Mediator creation data

        Returns:
            Created mediator
        """
        mediator = MediatorDB(**data.model_dump())
        self.session.add(mediator)
        await self.session.flush()
        return mediator

    async def get_mediator(self, mediator_id: UUID) -> MediatorDB | None:
        """
        Get a mediator by ID.

        Args:
            mediator_id: Mediator ID

        Returns:
            Mediator or None if not found
        """
        result = await self.session.execute(select(MediatorDB).where(MediatorDB.id == mediator_id))
        return result.scalar_one_or_none()

    async def list_mediators(
        self, project_id: UUID, is_active: bool | None = None
    ) -> list[MediatorDB]:
        """
        List mediators with optional filtering.

        Args:
            project_id: Project ID
            is_active: Filter by active status

        Returns:
            List of mediators
        """
        query = select(MediatorDB).where(MediatorDB.project_id == project_id)

        if is_active is not None:
            query = query.where(MediatorDB.is_active == is_active)

        query = query.order_by(MediatorDB.name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_mediator(self, mediator_id: UUID, data: MediatorUpdate) -> MediatorDB | None:
        """
        Update a mediator.

        Args:
            mediator_id: Mediator ID
            data: Update data

        Returns:
            Updated mediator or None if not found
        """
        update_data = data.model_dump(exclude_unset=True)

        result = await self.session.execute(
            update(MediatorDB)
            .where(MediatorDB.id == mediator_id)
            .values(**update_data)
            .returning(MediatorDB)
        )

        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_mediator(self, mediator_id: UUID) -> bool:
        """
        Delete a mediator.

        Args:
            mediator_id: Mediator ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(delete(MediatorDB).where(MediatorDB.id == mediator_id))
        await self.session.flush()
        return result.rowcount > 0

    # ========================================================================
    # Chat Room Mediator Assignment Operations
    # ========================================================================

    async def add_mediator_to_room(
        self, room_id: UUID, data: ChatRoomMediatorCreate
    ) -> ChatRoomMediatorDB:
        """
        Add a mediator to a chat room.

        Args:
            room_id: Room ID
            data: Assignment data

        Returns:
            Created assignment

        Raises:
            ValueError: If mediator already assigned to room
        """
        # Check for existing assignment
        existing = await self.session.execute(
            select(ChatRoomMediatorDB).where(
                ChatRoomMediatorDB.room_id == room_id,
                ChatRoomMediatorDB.mediator_id == data.mediator_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Mediator already assigned to this room")

        assignment = ChatRoomMediatorDB(room_id=room_id, **data.model_dump(exclude={"room_id"}))
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def get_room_mediator(
        self, room_id: UUID, mediator_id: UUID
    ) -> ChatRoomMediatorDB | None:
        """
        Get a specific room mediator assignment.

        Args:
            room_id: Room ID
            mediator_id: Mediator ID

        Returns:
            Assignment or None if not found
        """
        result = await self.session.execute(
            select(ChatRoomMediatorDB).where(
                ChatRoomMediatorDB.room_id == room_id,
                ChatRoomMediatorDB.mediator_id == mediator_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_room_mediators(
        self, room_id: UUID, is_active: bool | None = None
    ) -> list[ChatRoomMediatorDB]:
        """
        List all mediators assigned to a room.

        Args:
            room_id: Room ID
            is_active: Filter by active status

        Returns:
            List of assignments
        """
        query = select(ChatRoomMediatorDB).where(ChatRoomMediatorDB.room_id == room_id)

        if is_active is not None:
            query = query.where(ChatRoomMediatorDB.is_active == is_active)

        query = query.order_by(ChatRoomMediatorDB.joined_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_room_mediator(
        self, room_id: UUID, mediator_id: UUID, data: ChatRoomMediatorUpdate
    ) -> ChatRoomMediatorDB | None:
        """
        Update a room mediator assignment.

        Args:
            room_id: Room ID
            mediator_id: Mediator ID
            data: Update data

        Returns:
            Updated assignment or None if not found
        """
        update_data = data.model_dump(exclude_unset=True)

        result = await self.session.execute(
            update(ChatRoomMediatorDB)
            .where(
                ChatRoomMediatorDB.room_id == room_id,
                ChatRoomMediatorDB.mediator_id == mediator_id,
            )
            .values(**update_data)
            .returning(ChatRoomMediatorDB)
        )

        await self.session.flush()
        return result.scalar_one_or_none()

    async def remove_mediator_from_room(self, room_id: UUID, mediator_id: UUID) -> bool:
        """
        Remove a mediator from a chat room.

        Args:
            room_id: Room ID
            mediator_id: Mediator ID

        Returns:
            True if removed, False if not found
        """
        result = await self.session.execute(
            delete(ChatRoomMediatorDB).where(
                ChatRoomMediatorDB.room_id == room_id,
                ChatRoomMediatorDB.mediator_id == mediator_id,
            )
        )
        await self.session.flush()
        return result.rowcount > 0

    async def get_active_mediators_for_room(self, room_id: UUID) -> list[ChatRoomMediatorDB]:
        """
        Get all active mediators for a room.

        Args:
            room_id: Room ID

        Returns:
            List of active mediator assignments
        """
        result = await self.session.execute(
            select(ChatRoomMediatorDB).where(
                ChatRoomMediatorDB.room_id == room_id,
                ChatRoomMediatorDB.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
