"""
API endpoints for message history UI.

Provides endpoints for browsing and viewing message history
with filtering and pagination support.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from agent_comm_core.models.auth import User
from agent_comm_core.models.communication import Communication, CommunicationDirection
from agent_comm_core.services.communication import CommunicationService
from communication_server.dependencies import get_communication_service
from communication_server.security.dependencies import get_current_user

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageListItem(BaseModel):
    """Message item for list view."""

    message_id: str
    from_agent: str
    to_agent: str | None
    timestamp: datetime
    content_preview: str
    project_id: str | None
    message_type: str

    model_config = {"from_attributes": True}


class MessageDetail(BaseModel):
    """Full message details."""

    message_id: str
    from_agent: str
    to_agent: str
    timestamp: datetime
    content: str
    content_type: str = "text/plain"
    project_id: str | None
    message_type: str
    direction: CommunicationDirection
    correlation_id: UUID | None
    metadata: dict = {}

    model_config = {"from_attributes": True}


def create_content_preview(content: str, max_length: int = 100) -> str:
    """
    Create a preview of message content.

    Args:
        content: Full message content
        max_length: Maximum length for preview

    Returns:
        Truncated content with ellipsis if needed
    """
    if len(content) <= max_length:
        return content
    return content[:max_length].rstrip() + "..."


def determine_message_type(comm: Communication) -> str:
    """
    Determine the display message type from a communication.

    Args:
        comm: Communication record

    Returns:
        Message type string (direct, broadcast, reply)
    """
    # Check metadata for explicit message type
    if comm.metadata and "message_type" in comm.metadata:
        msg_type = comm.metadata["message_type"]
        if isinstance(msg_type, str):
            return msg_type

    # Determine from direction
    if comm.direction == CommunicationDirection.INBOUND:
        return "broadcast"
    elif comm.direction == CommunicationDirection.OUTBOUND:
        return "direct"
    else:
        # Check if it's a reply (has correlation_id)
        return "reply" if comm.correlation_id else "direct"


def extract_project_id(comm: Communication) -> str | None:
    """
    Extract project ID from communication metadata.

    Args:
        comm: Communication record

    Returns:
        Project ID or None
    """
    if comm.metadata and "project_id" in comm.metadata:
        proj_id = comm.metadata["project_id"]
        if isinstance(proj_id, str):
            return proj_id
    return None


@router.get("", response_model=list[MessageListItem])
async def list_messages(
    project_id: str | None = Query(None, description="Filter by project ID"),
    from_agent: str | None = Query(None, description="Filter by sender agent"),
    to_agent: str | None = Query(None, description="Filter by recipient agent"),
    limit: int = Query(50, ge=1, le=200, description="Messages per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user: User = Depends(get_current_user),  # noqa: ARG001
    service: CommunicationService = Depends(get_communication_service),
) -> list[MessageListItem]:
    """
    Get message history with optional filtering.

    Returns messages in reverse chronological order (newest first).
    Supports filtering by project, sender, and recipient.

    Args:
        project_id: Optional project ID filter
        from_agent: Optional sender agent filter
        to_agent: Optional recipient agent filter
        limit: Maximum number of results
        offset: Pagination offset
        user: Authenticated user (injected)
        service: Communication service (injected)

    Returns:
        List of message list items
    """
    try:
        # Get communications from service
        communications = await service.get_communications(
            from_agent=from_agent,
            to_agent=to_agent,
            limit=limit + offset,  # Fetch extra to support offset
        )

        # Apply offset and project filtering
        filtered = []
        for comm in communications:
            # Filter by project if specified
            if project_id:
                comm_project_id = extract_project_id(comm)
                if comm_project_id != project_id:
                    continue

            filtered.append(comm)

        # Apply pagination offset
        paginated = filtered[offset : offset + limit]

        # Convert to message list items
        message_items = []
        for comm in paginated:
            message_type = determine_message_type(comm)
            proj_id = extract_project_id(comm)
            content_preview = create_content_preview(comm.content)

            message_items.append(
                MessageListItem(
                    message_id=str(comm.id),
                    from_agent=comm.from_agent,
                    to_agent=comm.to_agent,
                    timestamp=comm.created_at,
                    content_preview=content_preview,
                    project_id=proj_id,
                    message_type=message_type,
                )
            )

        # Sort by timestamp descending (newest first)
        message_items.sort(key=lambda x: x.timestamp, reverse=True)

        return message_items

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}",
        ) from e


@router.get("/{message_id}", response_model=MessageDetail)
async def get_message_detail(
    message_id: str,
    user: User = Depends(get_current_user),  # noqa: ARG001
    service: CommunicationService = Depends(get_communication_service),
) -> MessageDetail:
    """
    Get full details of a specific message.

    Args:
        message_id: Message UUID string
        user: Authenticated user (injected)
        service: Communication service (injected)

    Returns:
        Full message details

    Raises:
        HTTPException: If message not found
    """
    try:
        comm_id = UUID(message_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID format",
        ) from e

    communication = await service.get_communication(comm_id)

    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )

    # Convert to message detail
    return MessageDetail(
        message_id=str(communication.id),
        from_agent=communication.from_agent,
        to_agent=communication.to_agent,
        timestamp=communication.created_at,
        content=communication.content,
        content_type="text/plain",
        project_id=extract_project_id(communication),
        message_type=determine_message_type(communication),
        direction=communication.direction,
        correlation_id=communication.correlation_id,
        metadata=communication.metadata,
    )
