"""
Mediator system service.

Provides business logic for mediator operations including
LLM provider integration and chat room message processing.
"""

from typing import Any
from uuid import UUID

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
from agent_comm_core.repositories.mediator import MediatorRepository
from agent_comm_core.services.llm_providers import (
    LLMRequest,
    LLMResponse,
    get_provider,
)


class MediatorService:
    """
    Service for mediator management and processing.

    Provides high-level operations for managing mediators,
    processing chat messages through LLM providers, and
    handling chat room assignments.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize service.

        Args:
            session: Database session
        """
        self.session = session
        self._repository = MediatorRepository(session)

    # ========================================================================
    # Mediator Model Management
    # ========================================================================

    async def create_model(self, data: MediatorModelCreate) -> MediatorModelDB:
        """
        Create a new mediator model.

        Args:
            data: Model creation data

        Returns:
            Created model
        """
        return await self._repository.create_model(data)

    async def get_model(self, model_id: UUID) -> MediatorModelDB | None:
        """
        Get a mediator model by ID.

        Args:
            model_id: Model ID

        Returns:
            Model or None if not found
        """
        return await self._repository.get_model(model_id)

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
        return await self._repository.list_models(provider, is_active)

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
        return await self._repository.update_model(model_id, data)

    async def delete_model(self, model_id: UUID) -> bool:
        """
        Delete a mediator model.

        Args:
            model_id: Model ID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete_model(model_id)

    # ========================================================================
    # Mediator Prompt Management
    # ========================================================================

    async def create_prompt(self, data: MediatorPromptCreate) -> MediatorPromptDB:
        """
        Create a new mediator prompt.

        Args:
            data: Prompt creation data

        Returns:
            Created prompt
        """
        return await self._repository.create_prompt(data)

    async def get_prompt(self, prompt_id: UUID) -> MediatorPromptDB | None:
        """
        Get a mediator prompt by ID.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt or None if not found
        """
        return await self._repository.get_prompt(prompt_id)

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
        return await self._repository.list_prompts(project_id, category, is_public, is_active)

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
        return await self._repository.update_prompt(prompt_id, data)

    async def delete_prompt(self, prompt_id: UUID) -> bool:
        """
        Delete a mediator prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete_prompt(prompt_id)

    async def duplicate_prompt(self, prompt_id: UUID, new_name: str) -> MediatorPromptDB | None:
        """
        Duplicate a mediator prompt.

        Args:
            prompt_id: Prompt ID to duplicate
            new_name: Name for the duplicated prompt

        Returns:
            Duplicated prompt or None if not found
        """
        original = await self._repository.get_prompt(prompt_id)
        if not original:
            return None

        duplicate_data = MediatorPromptCreate(
            project_id=original.project_id,
            name=new_name,
            description=original.description,
            category=original.category,
            system_prompt=original.system_prompt,
            variables=original.variables,
            examples=original.examples,
            is_public=False,
        )

        return await self._repository.create_prompt(duplicate_data)

    # ========================================================================
    # Mediator Management
    # ========================================================================

    async def create_mediator(self, data: MediatorCreate) -> MediatorDB:
        """
        Create a new mediator.

        Args:
            data: Mediator creation data

        Returns:
            Created mediator
        """
        # Validate model exists
        model = await self._repository.get_model(data.model_id)
        if not model:
            raise ValueError(f"Model {data.model_id} not found")

        # Validate default prompt if provided
        if data.default_prompt_id:
            prompt = await self._repository.get_prompt(data.default_prompt_id)
            if not prompt:
                raise ValueError(f"Prompt {data.default_prompt_id} not found")

        return await self._repository.create_mediator(data)

    async def get_mediator(self, mediator_id: UUID) -> MediatorDB | None:
        """
        Get a mediator by ID.

        Args:
            mediator_id: Mediator ID

        Returns:
            Mediator or None if not found
        """
        return await self._repository.get_mediator(mediator_id)

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
        return await self._repository.list_mediators(project_id, is_active)

    async def update_mediator(self, mediator_id: UUID, data: MediatorUpdate) -> MediatorDB | None:
        """
        Update a mediator.

        Args:
            mediator_id: Mediator ID
            data: Update data

        Returns:
            Updated mediator or None if not found
        """
        # Validate model if being updated
        if data.model_id:
            model = await self._repository.get_model(data.model_id)
            if not model:
                raise ValueError(f"Model {data.model_id} not found")

        # Validate default prompt if being updated
        if data.default_prompt_id:
            prompt = await self._repository.get_prompt(data.default_prompt_id)
            if not prompt:
                raise ValueError(f"Prompt {data.default_prompt_id} not found")

        return await self._repository.update_mediator(mediator_id, data)

    async def delete_mediator(self, mediator_id: UUID) -> bool:
        """
        Delete a mediator.

        Args:
            mediator_id: Mediator ID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete_mediator(mediator_id)

    # ========================================================================
    # Chat Room Mediator Assignment
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
            ValueError: If mediator already assigned or not found
        """
        # Validate mediator exists
        mediator = await self._repository.get_mediator(data.mediator_id)
        if not mediator:
            raise ValueError(f"Mediator {data.mediator_id} not found")

        # Validate prompt override if provided
        if data.prompt_id:
            prompt = await self._repository.get_prompt(data.prompt_id)
            if not prompt:
                raise ValueError(f"Prompt {data.prompt_id} not found")

        return await self._repository.add_mediator_to_room(room_id, data)

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
        return await self._repository.get_room_mediator(room_id, mediator_id)

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
        return await self._repository.list_room_mediators(room_id, is_active)

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
        # Validate prompt override if being updated
        if data.prompt_id:
            prompt = await self._repository.get_prompt(data.prompt_id)
            if not prompt:
                raise ValueError(f"Prompt {data.prompt_id} not found")

        return await self._repository.update_room_mediator(room_id, mediator_id, data)

    async def remove_mediator_from_room(self, room_id: UUID, mediator_id: UUID) -> bool:
        """
        Remove a mediator from a chat room.

        Args:
            room_id: Room ID
            mediator_id: Mediator ID

        Returns:
            True if removed, False if not found
        """
        return await self._repository.remove_mediator_from_room(room_id, mediator_id)

    # ========================================================================
    # Mediator Processing
    # ========================================================================

    async def trigger_mediator(
        self,
        room_id: UUID,
        mediator_id: UUID,
        message_content: str,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Manually trigger a mediator to process a message.

        Args:
            room_id: Room ID
            mediator_id: Mediator ID
            message_content: Message content to process
            context: Additional context for processing

        Returns:
            LLM response

        Raises:
            ValueError: If mediator not found or not assigned to room
        """
        # Get room assignment
        assignment = await self._repository.get_room_mediator(room_id, mediator_id)
        if not assignment:
            raise ValueError(f"Mediator {mediator_id} not assigned to room {room_id}")

        if not assignment.is_active:
            raise ValueError(f"Mediator {mediator_id} is not active")

        # Get mediator with relationships
        mediator = await self.get_mediator(mediator_id)
        if not mediator:
            raise ValueError(f"Mediator {mediator_id} not found")

        return await self._process_mediator_message(mediator, assignment, message_content, context)

    async def process_active_mediators(
        self, room_id: UUID, message_content: str, context: dict[str, Any] | None = None
    ) -> list[tuple[UUID, LLMResponse]]:
        """
        Process message through all active auto-trigger mediators in a room.

        Args:
            room_id: Room ID
            message_content: Message content to process
            context: Additional context for processing

        Returns:
            List of (mediator_id, response) tuples
        """
        assignments = await self._repository.get_active_mediators_for_room(room_id)

        results = []
        for assignment in assignments:
            # Check if should trigger
            if not self._should_trigger_mediator(assignment, message_content):
                continue

            try:
                mediator = await self.get_mediator(assignment.mediator_id)
                if mediator and mediator.is_active:
                    response = await self._process_mediator_message(
                        mediator, assignment, message_content, context
                    )
                    results.append((assignment.mediator_id, response))
            except Exception:
                # Log error but continue processing other mediators
                pass

        return results

    def _should_trigger_mediator(
        self, assignment: ChatRoomMediatorDB, message_content: str
    ) -> bool:
        """
        Determine if a mediator should trigger based on configuration.

        Args:
            assignment: Room mediator assignment
            message_content: Message content to check

        Returns:
            True if mediator should trigger
        """
        # Auto-trigger always responds
        if assignment.auto_trigger:
            return True

        # Check trigger keywords
        if assignment.trigger_keywords:
            message_lower = message_content.lower()
            for keyword in assignment.trigger_keywords:
                if keyword.lower() in message_lower:
                    return True

        return False

    async def _process_mediator_message(
        self,
        mediator: MediatorDB,
        assignment: ChatRoomMediatorDB,
        message_content: str,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Process a message through a mediator.

        Args:
            mediator: Mediator configuration
            assignment: Room assignment
            message_content: Message to process
            context: Additional context

        Returns:
            LLM response

        Raises:
            ValueError: If model not found or provider unavailable
        """
        # Get model
        model = await self._repository.get_model(mediator.model_id)
        if not model:
            raise ValueError(f"Model {mediator.model_id} not found")

        # Get prompt (use override if available, otherwise default)
        prompt_id = assignment.prompt_id or mediator.default_prompt_id
        system_prompt = mediator.system_prompt

        if prompt_id:
            prompt = await self._repository.get_prompt(prompt_id)
            if prompt:
                system_prompt = prompt.system_prompt

        if not system_prompt:
            system_prompt = "You are a helpful AI assistant participating in a chat conversation."

        # Build additional context
        additional_context = context or {}
        additional_context.update(
            {
                "room_id": str(assignment.room_id),
                "mediator_id": str(mediator.id),
                "mediator_name": mediator.name,
            }
        )

        # Get LLM provider
        try:
            provider = get_provider(model.provider)
        except ValueError as e:
            raise ValueError(f"Provider {model.provider} not available: {e}") from e

        # Build LLM request
        request = LLMRequest(
            system_prompt=system_prompt,
            user_message=message_content,
            temperature=float(mediator.temperature or "0.7"),
            max_tokens=int(mediator.max_tokens) if mediator.max_tokens else None,
            model_id=model.model_id,
            api_endpoint=model.api_endpoint,
            additional_context=additional_context,
        )

        # Generate response
        return await provider.generate(request)

    # ========================================================================
    # Seed Data
    # ========================================================================

    async def seed_default_models(self) -> list[MediatorModelDB]:
        """
        Seed default LLM models if they don't exist.

        Returns:
            List of created/existing models
        """
        default_models = [
            MediatorModelCreate(
                name="GPT-4 Turbo",
                provider="openai",
                model_id="gpt-4-turbo-preview",
                max_tokens=128000,
                supports_streaming=True,
                supports_function_calling=True,
            ),
            MediatorModelCreate(
                name="GPT-4",
                provider="openai",
                model_id="gpt-4",
                max_tokens=8192,
                supports_streaming=True,
                supports_function_calling=True,
            ),
            MediatorModelCreate(
                name="GPT-3.5 Turbo",
                provider="openai",
                model_id="gpt-3.5-turbo",
                max_tokens=16385,
                supports_streaming=True,
                supports_function_calling=True,
            ),
            MediatorModelCreate(
                name="Claude 3 Opus",
                provider="anthropic",
                model_id="claude-3-opus-20240229",
                max_tokens=200000,
                supports_streaming=True,
                supports_function_calling=True,
            ),
            MediatorModelCreate(
                name="Claude 3 Sonnet",
                provider="anthropic",
                model_id="claude-3-sonnet-20240229",
                max_tokens=200000,
                supports_streaming=True,
                supports_function_calling=True,
            ),
            MediatorModelCreate(
                name="Claude 3 Haiku",
                provider="anthropic",
                model_id="claude-3-haiku-20240307",
                max_tokens=200000,
                supports_streaming=True,
                supports_function_calling=False,
            ),
        ]

        created = []
        for model_data in default_models:
            existing = await self._repository.get_model_by_name(model_data.name)
            if not existing:
                model = await self._repository.create_model(model_data)
                created.append(model)
            else:
                created.append(existing)

        return created
