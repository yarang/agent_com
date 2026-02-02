"""
Chat room API endpoints for real-time messaging.

Provides CRUD operations for chat rooms, participants, and messages.
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_comm_core.db.database import db_session
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.chat import (
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatParticipantAdd,
    ChatParticipantResponse,
    ChatRoomCreate,
    ChatRoomResponse,
    ChatRoomUpdate,
    MessageType,
    SenderType,
)
from agent_comm_core.repositories import ChatRepository
from communication_server.security.authorization import Permission, require_permission

router = APIRouter(prefix="/chat", tags=["Chat"])

# ============================================================================
# Request/Response Models
# ============================================================================


class MessageListParams(BaseModel):
    """Query parameters for message list."""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=1000, description="Messages per page")


# ============================================================================
# Chat Room Endpoints
# ============================================================================


@router.post("/rooms", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """
    Create a new chat room.

    Requires PROJECT_CREATE permission. Associates the room with a project
    and automatically adds the creator as a participant.

    Args:
        room_data: Chat room creation data
        current_user: Current authenticated user

    Returns:
        Created chat room

    Raises:
        HTTPException: If project not found or access denied
    """
    async with db_session() as session:
        from sqlalchemy import select

        # Verify project exists and user has access
        project_result = await session.execute(
            select(ProjectDB).where(ProjectDB.id == room_data.project_id)
        )
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Check project access
        if not current_user.is_superuser and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project",
            )

        # Create chat room
        repo = ChatRepository(session)
        room = await repo.create_room(
            project_id=room_data.project_id,
            name=room_data.name,
            description=room_data.description,
            created_by=current_user.id,
        )

        # Add creator as participant
        await repo.add_participant(room.id, user_id=current_user.id)

        await session.commit()
        await session.refresh(room)

        return ChatRoomResponse(
            id=room.id,
            project_id=room.project_id,
            name=room.name,
            description=room.description,
            created_by=room.created_by,
            created_at=room.created_at,
            updated_at=room.updated_at,
            participant_count=1,
            message_count=0,
        )


@router.get("/rooms", response_model=list[ChatRoomResponse])
async def list_chat_rooms(
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List chat rooms accessible to the current user.

    Requires PROJECT_READ permission.

    Args:
        current_user: Current authenticated user
        project_id: Optional project filter
        skip: Number of rooms to skip
        limit: Maximum number of rooms to return

    Returns:
        List of chat rooms
    """
    async with db_session() as session:
        repo = ChatRepository(session)

        # Get rooms
        rooms = await repo.list_rooms(project_id=project_id, limit=limit, offset=skip)

        # Filter by project access
        result = []
        for room in rooms:
            # Check access to project
            if current_user.is_superuser or room.project_id == current_user.id:
                participant_count = await repo.get_room_participant_count(room.id)
                message_count = await repo.get_room_message_count(room.id)
                result.append(
                    ChatRoomResponse(
                        id=room.id,
                        project_id=room.project_id,
                        name=room.name,
                        description=room.description,
                        created_by=room.created_by,
                        created_at=room.created_at,
                        updated_at=room.updated_at,
                        participant_count=participant_count,
                        message_count=message_count,
                    )
                )

        return result


@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
async def get_chat_room(
    room_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
):
    """
    Get a chat room by ID.

    Requires PROJECT_READ permission and participant access.

    Args:
        room_id: Room UUID
        current_user: Current authenticated user

    Returns:
        Chat room details

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Verify user is a participant
        is_participant = await repo.is_participant(room.id, user_id=current_user.id)
        if not is_participant and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this room",
            )

        participant_count = await repo.get_room_participant_count(room.id)
        message_count = await repo.get_room_message_count(room.id)

        return ChatRoomResponse(
            id=room.id,
            project_id=room.project_id,
            name=room.name,
            description=room.description,
            created_by=room.created_by,
            created_at=room.created_at,
            updated_at=room.updated_at,
            participant_count=participant_count,
            message_count=message_count,
        )


@router.put("/rooms/{room_id}", response_model=ChatRoomResponse)
async def update_chat_room(
    room_id: UUID,
    room_data: ChatRoomUpdate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Update a chat room.

    Requires PROJECT_UPDATE permission and room ownership.

    Args:
        room_id: Room UUID
        room_data: Update data
        current_user: Current authenticated user

    Returns:
        Updated chat room

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Check ownership (creator)
        if room.created_by != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this room",
            )

        # Update room
        updated = await repo.update_room(room_id, room_data)
        await session.commit()
        await session.refresh(updated)

        participant_count = await repo.get_room_participant_count(room.id)
        message_count = await repo.get_room_message_count(room.id)

        return ChatRoomResponse(
            id=updated.id,
            project_id=updated.project_id,
            name=updated.name,
            description=updated.description,
            created_by=updated.created_by,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            participant_count=participant_count,
            message_count=message_count,
        )


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_room(
    room_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_DELETE))],
):
    """
    Delete a chat room.

    Requires PROJECT_DELETE permission and room ownership.

    Args:
        room_id: Room UUID
        current_user: Current authenticated user

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Check ownership (creator)
        if room.created_by != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this room",
            )

        await repo.delete_room(room_id)
        await session.commit()


# ============================================================================
# Participant Endpoints
# ============================================================================


@router.post(
    "/rooms/{room_id}/participants",
    response_model=ChatParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_chat_participant(
    room_id: UUID,
    participant_data: ChatParticipantAdd,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Add a participant to a chat room.

    Requires PROJECT_UPDATE permission and room ownership.

    Args:
        room_id: Room UUID
        participant_data: Participant data (agent_id or user_id)
        current_user: Current authenticated user

    Returns:
        Created participant

    Raises:
        HTTPException: If room not found, access denied, or validation fails
    """
    if not participant_data.agent_id and not participant_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either agent_id or user_id must be provided",
        )

    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Check ownership
        if room.created_by != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this room",
            )

        # Check if already participant
        is_existing = await repo.is_participant(
            room_id, user_id=participant_data.user_id, agent_id=participant_data.agent_id
        )
        if is_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already a participant in this room",
            )

        # Add participant
        participant = await repo.add_participant(
            room_id=room_id,
            agent_id=participant_data.agent_id,
            user_id=participant_data.user_id,
        )
        await session.commit()
        await session.refresh(participant)

        return ChatParticipantResponse(
            id=participant.id,
            room_id=participant.room_id,
            agent_id=participant.agent_id,
            user_id=participant.user_id,
            joined_at=participant.joined_at,
        )


@router.get("/rooms/{room_id}/participants", response_model=list[ChatParticipantResponse])
async def list_chat_participants(
    room_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
):
    """
    List all participants in a chat room.

    Requires PROJECT_READ permission and participant access.

    Args:
        room_id: Room UUID
        current_user: Current authenticated user

    Returns:
        List of participants

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Verify user is a participant
        is_participant = await repo.is_participant(room.id, user_id=current_user.id)
        if not is_participant and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this room",
            )

        participants = await repo.get_participants(room_id)

        return [
            ChatParticipantResponse(
                id=p.id,
                room_id=p.room_id,
                agent_id=p.agent_id,
                user_id=p.user_id,
                joined_at=p.joined_at,
            )
            for p in participants
        ]


@router.delete(
    "/rooms/{room_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_chat_participant(
    room_id: UUID,
    participant_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Remove a participant from a chat room.

    Requires PROJECT_UPDATE permission and room ownership.

    Args:
        room_id: Room UUID
        participant_id: Participant UUID
        current_user: Current authenticated user

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Check ownership
        if room.created_by != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this room",
            )

        await repo.remove_participant(participant_id)
        await session.commit()


# ============================================================================
# Message Endpoints
# ============================================================================


@router.post(
    "/rooms/{room_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_chat_message(
    room_id: UUID,
    message_data: ChatMessageCreate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
):
    """
    Send a message to a chat room.

    Requires PROJECT_READ permission and participant access.

    Args:
        room_id: Room UUID
        message_data: Message data
        current_user: Current authenticated user

    Returns:
        Created message

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Verify user is a participant
        is_participant = await repo.is_participant(room.id, user_id=current_user.id)
        if not is_participant and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this room",
            )

        # Create message
        message = await repo.create_message(
            room_id=room_id,
            sender_type=SenderType.USER,
            sender_id=current_user.id,
            content=message_data.content,
            message_type=message_data.message_type.value,
            metadata=message_data.metadata,
        )
        await session.commit()
        await session.refresh(message)

        # Broadcast to WebSocket connections
        from communication_server.websocket.chat_manager import get_chat_manager

        chat_manager = get_chat_manager()
        await chat_manager.broadcast_message(
            room_id=room_id,
            message_id=message.id,
            sender_type=SenderType.USER.value,
            sender_id=current_user.id,
            content=message_data.content,
            message_type=message_data.message_type.value,
        )

        return ChatMessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_type=SenderType(message.sender_type),
            sender_id=message.sender_id,
            content=message.content,
            message_type=MessageType(message.message_type),
            metadata=message.metadata,
            created_at=message.created_at,
        )


@router.get("/rooms/{room_id}/messages", response_model=ChatMessageListResponse)
async def get_chat_messages(
    room_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
):
    """
    Get messages from a chat room with pagination.

    Requires PROJECT_READ permission and participant access.

    Args:
        room_id: Room UUID
        current_user: Current authenticated user
        page: Page number (1-indexed)
        page_size: Messages per page

    Returns:
        Paginated message list

    Raises:
        HTTPException: If room not found or access denied
    """
    async with db_session() as session:
        repo = ChatRepository(session)
        room = await repo.get_room(room_id)

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found",
            )

        # Verify user is a participant
        is_participant = await repo.is_participant(room.id, user_id=current_user.id)
        if not is_participant and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this room",
            )

        # Get messages
        total = await repo.get_message_count(room_id)
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (page - 1) * page_size

        messages = await repo.get_messages(room_id=room_id, limit=page_size, offset=offset)

        return ChatMessageListResponse(
            messages=[
                ChatMessageResponse(
                    id=m.id,
                    room_id=m.room_id,
                    sender_type=SenderType(m.sender_type),
                    sender_id=m.sender_id,
                    content=m.content,
                    message_type=MessageType(m.message_type),
                    metadata=m.metadata,
                    created_at=m.created_at,
                )
                for m in messages
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=page < total_pages,
        )
