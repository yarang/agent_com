"""
API endpoints for meeting management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.meeting import (
    Meeting,
    MeetingCreate,
    MeetingMessage,
    MeetingParticipant,
    MeetingStatus,
)
from agent_comm_core.services.meeting import MeetingService

from communication_server.dependencies import (
    get_db_session,
    get_meeting_service,
)
from communication_server.analyzer.topic import TopicAnalyzer, AgendaSuggestion
from communication_server.repositories.meeting import SQLALchemyMeetingRepository
from communication_server.websocket.manager import ConnectionManager


router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=Meeting, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    service: MeetingService = Depends(get_meeting_service),
) -> Meeting:
    """
    Create a new meeting.

    Args:
        data: Meeting creation data
        service: Meeting service (injected)

    Returns:
        The created meeting
    """
    try:
        return await service.create_meeting(
            title=data.title,
            participant_ids=data.participant_ids,
            description=data.description,
            agenda=data.agenda,
            max_duration_seconds=data.max_duration_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[Meeting])
async def list_meetings(
    status: Optional[MeetingStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    service: MeetingService = Depends(get_meeting_service),
) -> list[Meeting]:
    """
    List meetings with optional filtering.

    Args:
        status: Optional status filter
        limit: Maximum number of results
        service: Meeting service (injected)

    Returns:
        List of meetings
    """
    if status:
        return await service.get_meetings_by_status(status)
    # Return all meetings via repository
    return []


@router.get("/{meeting_id}", response_model=Meeting)
async def get_meeting(
    meeting_id: UUID,
    service: MeetingService = Depends(get_meeting_service),
) -> Meeting:
    """
    Get a specific meeting by ID.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        The meeting record

    Raises:
        HTTPException: If meeting not found
    """
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )
    return meeting


@router.post("/{meeting_id}/start", response_model=Meeting)
async def start_meeting(
    meeting_id: UUID,
    service: MeetingService = Depends(get_meeting_service),
) -> Meeting:
    """
    Start a meeting.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        The updated meeting

    Raises:
        HTTPException: If meeting not found
    """
    meeting = await service.start_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )
    return meeting


@router.post("/{meeting_id}/end", response_model=Meeting)
async def end_meeting(
    meeting_id: UUID,
    service: MeetingService = Depends(get_meeting_service),
) -> Meeting:
    """
    End a meeting.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        The updated meeting

    Raises:
        HTTPException: If meeting not found
    """
    meeting = await service.end_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )
    return meeting


@router.get("/{meeting_id}/participants", response_model=list[MeetingParticipant])
async def get_meeting_participants(
    meeting_id: UUID,
    service: MeetingService = Depends(get_meeting_service),
) -> list[MeetingParticipant]:
    """
    Get all participants for a meeting.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        List of meeting participants
    """
    return await service.get_participants(meeting_id)


@router.post(
    "/{meeting_id}/participants",
    response_model=MeetingParticipant,
    status_code=status.HTTP_201_CREATED,
)
async def add_meeting_participant(
    meeting_id: UUID,
    agent_id: str,
    role: str = Query("participant", description="Participant role"),
    service: MeetingService = Depends(get_meeting_service),
) -> MeetingParticipant:
    """
    Add a participant to a meeting.

    Args:
        meeting_id: Meeting ID
        agent_id: Agent identifier
        role: Participant role
        service: Meeting service (injected)

    Returns:
        The created participant
    """
    return await service.add_participant(meeting_id, agent_id, role)


@router.get("/{meeting_id}/messages", response_model=list[MeetingMessage])
async def get_meeting_messages(
    meeting_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    service: MeetingService = Depends(get_meeting_service),
) -> list[MeetingMessage]:
    """
    Get messages from a meeting.

    Args:
        meeting_id: Meeting ID
        limit: Maximum number of results
        service: Meeting service (injected)

    Returns:
        List of meeting messages
    """
    return await service.get_messages(meeting_id, limit)


@router.post(
    "/{meeting_id}/messages", response_model=MeetingMessage, status_code=status.HTTP_201_CREATED
)
async def record_meeting_message(
    meeting_id: UUID,
    agent_id: str,
    content: str,
    message_type: str = Query("statement", description="Message type"),
    service: MeetingService = Depends(get_meeting_service),
) -> MeetingMessage:
    """
    Record a message in a meeting.

    Args:
        meeting_id: Meeting ID
        agent_id: Agent identifier
        content: Message content
        message_type: Type of message
        service: Meeting service (injected)

    Returns:
        The created message
    """
    try:
        return await service.record_message(
            meeting_id=meeting_id,
            agent_id=agent_id,
            content=content,
            message_type=message_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{meeting_id}/agenda/suggestions", response_model=list[AgendaSuggestion])
async def get_agenda_suggestions(
    meeting_id: UUID,
    max_items: int = Query(5, ge=1, le=10, description="Maximum agenda items"),
    max_duration: int = Query(60, ge=15, le=240, description="Maximum meeting duration in minutes"),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgendaSuggestion]:
    """
    Get agenda suggestions for a meeting based on recent communications.

    Args:
        meeting_id: Meeting ID
        max_items: Maximum number of agenda items
        max_duration: Maximum meeting duration in minutes
        session: Database session (injected)

    Returns:
        List of agenda suggestions
    """
    # Get meeting details to filter by participants
    repo = SQLALchemyMeetingRepository(session)
    meeting = await repo.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )

    participants = await repo.get_participants(meeting_id)
    participant_ids = {p.agent_id for p in participants}

    # Analyze communications for topics
    analyzer = TopicAnalyzer(session)
    topics = await analyzer.analyze_communications(
        agent_filter=participant_ids,
        min_communications=2,
    )

    # Generate agenda suggestions
    return await analyzer.suggest_agenda(
        topics=topics,
        max_items=max_items,
        max_duration_minutes=max_duration,
    )


@router.get("/agenda/analyze", response_model=list[AgendaSuggestion])
async def analyze_agenda_topics(
    agent_ids: str = Query(..., description="Comma-separated list of agent IDs"),
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    max_items: int = Query(5, ge=1, le=10, description="Maximum agenda items"),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgendaSuggestion]:
    """
    Analyze recent communications for agenda topics.

    Args:
        agent_ids: Comma-separated list of agent IDs to analyze
        time_range_hours: Time range to analyze in hours
        max_items: Maximum number of agenda items
        session: Database session (injected)

    Returns:
        List of agenda suggestions
    """
    participant_ids = {aid.strip() for aid in agent_ids.split(",") if aid.strip()}

    analyzer = TopicAnalyzer(session)
    topics = await analyzer.analyze_communications(
        time_range_hours=time_range_hours,
        agent_filter=participant_ids,
        min_communications=2,
    )

    return await analyzer.suggest_agenda(topics=topics, max_items=max_items)
