"""
API endpoints for mediator system.

Provides REST API for managing mediators, models, prompts,
and chat room assignments.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.mediator import (
    ChatRoomMediatorCreate,
    ChatRoomMediatorDetailResponse,
    ChatRoomMediatorResponse,
    ChatRoomMediatorUpdate,
    MediatorCreate,
    MediatorDetailResponse,
    MediatorModelCreate,
    MediatorModelResponse,
    MediatorModelUpdate,
    MediatorPromptCategory,
    MediatorPromptCreate,
    MediatorPromptDuplicate,
    MediatorPromptResponse,
    MediatorPromptUpdate,
    MediatorResponse,
    MediatorUpdate,
)
from agent_comm_core.services.mediator import MediatorService
from communication_server.dependencies import get_db_session

router = APIRouter(tags=["mediators"])


# ============================================================================
# Dependencies
# ============================================================================


async def get_mediator_service(
    session: AsyncSession = Depends(get_db_session),
) -> MediatorService:
    """
    Get mediator service instance.

    Args:
        session: Database session

    Returns:
        Mediator service instance
    """
    return MediatorService(session)


# ============================================================================
# Mediator Model Management
# ============================================================================


@router.get("/mediator-models", response_model=list[MediatorModelResponse])
async def list_mediator_models(
    provider: str | None = Query(None, description="Filter by provider"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    service: MediatorService = Depends(get_mediator_service),
) -> list[MediatorModelResponse]:
    """
    List available mediator models.

    Returns all LLM models configured for mediators,
    optionally filtered by provider and active status.
    """
    models = await service.list_models(provider=provider, is_active=is_active)
    return [MediatorModelResponse.model_validate(m) for m in models]


@router.get("/mediator-models/{model_id}", response_model=MediatorModelResponse)
async def get_mediator_model(
    model_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorModelResponse:
    """Get details of a specific mediator model."""
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )
    return MediatorModelResponse.model_validate(model)


@router.post(
    "/mediator-models", response_model=MediatorModelResponse, status_code=status.HTTP_201_CREATED
)
async def create_mediator_model(
    data: MediatorModelCreate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorModelResponse:
    """
    Create a new mediator model.

    Requires admin privileges.
    """
    model = await service.create_model(data)
    return MediatorModelResponse.model_validate(model)


@router.put("/mediator-models/{model_id}", response_model=MediatorModelResponse)
async def update_mediator_model(
    model_id: UUID,
    data: MediatorModelUpdate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorModelResponse:
    """
    Update a mediator model.

    Requires admin privileges.
    """
    model = await service.update_model(model_id, data)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )
    return MediatorModelResponse.model_validate(model)


@router.delete("/mediator-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mediator_model(
    model_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> None:
    """
    Delete a mediator model.

    Requires admin privileges.
    """
    success = await service.delete_model(model_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )


# ============================================================================
# Mediator Prompt Management
# ============================================================================


@router.get("/mediator-prompts/categories", response_model=list[str])
async def list_prompt_categories() -> list[str]:
    """List available prompt categories."""
    return [category.value for category in MediatorPromptCategory]


@router.get("/projects/{project_id}/mediator-prompts", response_model=list[MediatorPromptResponse])
async def list_mediator_prompts(
    project_id: UUID,
    category: str | None = Query(None, description="Filter by category"),
    is_public: bool | None = Query(None, description="Filter by public status"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    service: MediatorService = Depends(get_mediator_service),
) -> list[MediatorPromptResponse]:
    """List mediator prompts for a project."""
    prompts = await service.list_prompts(
        project_id=project_id,
        category=category,
        is_public=is_public,
        is_active=is_active,
    )
    return [MediatorPromptResponse.model_validate(p) for p in prompts]


@router.get("/mediator-prompts/{prompt_id}", response_model=MediatorPromptResponse)
async def get_mediator_prompt(
    prompt_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorPromptResponse:
    """Get details of a specific mediator prompt."""
    prompt = await service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found",
        )
    return MediatorPromptResponse.model_validate(prompt)


@router.post(
    "/projects/{project_id}/mediator-prompts",
    response_model=MediatorPromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mediator_prompt(
    project_id: UUID,
    data: MediatorPromptCreate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorPromptResponse:
    """Create a new mediator prompt."""
    # Ensure project_id matches
    data.project_id = project_id
    prompt = await service.create_prompt(data)
    return MediatorPromptResponse.model_validate(prompt)


@router.put("/mediator-prompts/{prompt_id}", response_model=MediatorPromptResponse)
async def update_mediator_prompt(
    prompt_id: UUID,
    data: MediatorPromptUpdate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorPromptResponse:
    """Update a mediator prompt."""
    prompt = await service.update_prompt(prompt_id, data)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found",
        )
    return MediatorPromptResponse.model_validate(prompt)


@router.delete("/mediator-prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mediator_prompt(
    prompt_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> None:
    """Delete a mediator prompt."""
    success = await service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found",
        )


@router.post(
    "/mediator-prompts/{prompt_id}/duplicate",
    response_model=MediatorPromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_mediator_prompt(
    prompt_id: UUID,
    data: MediatorPromptDuplicate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorPromptResponse:
    """Duplicate an existing mediator prompt."""
    prompt = await service.duplicate_prompt(prompt_id, data.name)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found",
        )
    return MediatorPromptResponse.model_validate(prompt)


# ============================================================================
# Mediator Management
# ============================================================================


@router.get("/projects/{project_id}/mediators", response_model=list[MediatorResponse])
async def list_mediators(
    project_id: UUID,
    is_active: bool | None = Query(None, description="Filter by active status"),
    service: MediatorService = Depends(get_mediator_service),
) -> list[MediatorResponse]:
    """List mediators for a project."""
    mediators = await service.list_mediators(project_id=project_id, is_active=is_active)
    return [MediatorResponse.model_validate(m) for m in mediators]


@router.get("/mediators/{mediator_id}", response_model=MediatorDetailResponse)
async def get_mediator(
    mediator_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorDetailResponse:
    """Get details of a specific mediator."""
    mediator = await service.get_mediator(mediator_id)
    if not mediator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mediator {mediator_id} not found",
        )

    # Load related data
    model = await service.get_model(mediator.model_id)
    default_prompt = None
    if mediator.default_prompt_id:
        default_prompt = await service.get_prompt(mediator.default_prompt_id)

    return MediatorDetailResponse(
        **mediator.__dict__,
        model=MediatorModelResponse.model_validate(model) if model else None,
        default_prompt=MediatorPromptResponse.model_validate(default_prompt)
        if default_prompt
        else None,
    )


@router.post(
    "/projects/{project_id}/mediators",
    response_model=MediatorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mediator(
    project_id: UUID,
    data: MediatorCreate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorResponse:
    """Create a new mediator."""
    # Ensure project_id matches
    data.project_id = project_id
    mediator = await service.create_mediator(data)
    return MediatorResponse.model_validate(mediator)


@router.put("/mediators/{mediator_id}", response_model=MediatorResponse)
async def update_mediator(
    mediator_id: UUID,
    data: MediatorUpdate,
    service: MediatorService = Depends(get_mediator_service),
) -> MediatorResponse:
    """Update a mediator."""
    mediator = await service.update_mediator(mediator_id, data)
    if not mediator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mediator {mediator_id} not found",
        )
    return MediatorResponse.model_validate(mediator)


@router.delete("/mediators/{mediator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mediator(
    mediator_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> None:
    """Delete a mediator."""
    success = await service.delete_mediator(mediator_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mediator {mediator_id} not found",
        )


# ============================================================================
# Chat Room Mediator Assignment
# ============================================================================


@router.get("/chat/rooms/{room_id}/mediators", response_model=list[ChatRoomMediatorDetailResponse])
async def list_room_mediators(
    room_id: UUID,
    is_active: bool | None = Query(None, description="Filter by active status"),
    service: MediatorService = Depends(get_mediator_service),
) -> list[ChatRoomMediatorDetailResponse]:
    """List all mediators assigned to a chat room."""
    assignments = await service.list_room_mediators(room_id=room_id, is_active=is_active)

    result = []
    for assignment in assignments:
        # Load related data
        mediator = await service.get_mediator(assignment.mediator_id)
        prompt_override = None
        if assignment.prompt_id:
            prompt_override = await service.get_prompt(assignment.prompt_id)

        result.append(
            ChatRoomMediatorDetailResponse(
                **assignment.__dict__,
                mediator=MediatorResponse.model_validate(mediator) if mediator else None,
                prompt_override=MediatorPromptResponse.model_validate(prompt_override)
                if prompt_override
                else None,
            )
        )

    return result


@router.post(
    "/chat/rooms/{room_id}/mediators",
    response_model=ChatRoomMediatorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_mediator_to_room(
    room_id: UUID,
    data: ChatRoomMediatorCreate,
    service: MediatorService = Depends(get_mediator_service),
) -> ChatRoomMediatorResponse:
    """Add a mediator to a chat room."""
    assignment = await service.add_mediator_to_room(room_id=room_id, data=data)
    return ChatRoomMediatorResponse.model_validate(assignment)


@router.put(
    "/chat/rooms/{room_id}/mediators/{mediator_id}", response_model=ChatRoomMediatorResponse
)
async def update_room_mediator(
    room_id: UUID,
    mediator_id: UUID,
    data: ChatRoomMediatorUpdate,
    service: MediatorService = Depends(get_mediator_service),
) -> ChatRoomMediatorResponse:
    """Update mediator assignment for a chat room."""
    assignment = await service.update_room_mediator(
        room_id=room_id, mediator_id=mediator_id, data=data
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mediator {mediator_id} not assigned to room {room_id}",
        )
    return ChatRoomMediatorResponse.model_validate(assignment)


@router.delete(
    "/chat/rooms/{room_id}/mediators/{mediator_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_mediator_from_room(
    room_id: UUID,
    mediator_id: UUID,
    service: MediatorService = Depends(get_mediator_service),
) -> None:
    """Remove a mediator from a chat room."""
    success = await service.remove_mediator_from_room(room_id=room_id, mediator_id=mediator_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mediator {mediator_id} not assigned to room {room_id}",
        )


@router.post("/chat/rooms/{room_id}/mediators/{mediator_id}/trigger", response_model=dict[str, Any])
async def trigger_mediator(
    room_id: UUID,
    mediator_id: UUID,
    message_content: str = Query(..., description="Message content to process"),
    context: dict[str, Any] | None = None,
    service: MediatorService = Depends(get_mediator_service),
) -> dict[str, Any]:
    """
    Manually trigger a mediator to process a message.

    Returns the mediator's response.
    """
    try:
        response = await service.trigger_mediator(
            room_id=room_id,
            mediator_id=mediator_id,
            message_content=message_content,
            context=context,
        )

        return {
            "mediator_id": mediator_id,
            "room_id": room_id,
            "response": response.content,
            "model_used": response.model_used,
            "tokens_used": response.tokens_used,
            "processed_at": datetime.now(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
