"""
API endpoints for SPEC-AGENT-COMM-001.

Provides REST API endpoints for agent communications, meetings, and decisions
as specified in SPEC-AGENT-COMM-001.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.agent_comm import (
    CommunicationCreate,
    CommunicationListResponse,
    CommunicationResponse,
    DecisionCreate,
    DecisionListResponse,
    DecisionResponse,
    MeetingCreate,
    MeetingDetailResponse,
    MeetingMessageCreate,
    MeetingMessageResponse,
    MeetingParticipantResponse,
    MeetingResponse,
    SuggestedTopic,
    TopicSuggestionResponse,
)
from communication_server.dependencies import get_db_session
from communication_server.services.agent_comm import (
    AgentCommunicationService,
    AgentDecisionService,
    AgentMeetingService,
    SequentialDiscussionAlgorithm,
    TopicAnalyzer,
)

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(prefix="/agent-comm", tags=["agent-comm"])


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_communication_service(
    session: AsyncSession = Depends(get_db_session),
) -> AgentCommunicationService:
    """Get communication service instance."""
    return AgentCommunicationService(session)


async def get_meeting_service(
    session: AsyncSession = Depends(get_db_session),
) -> AgentMeetingService:
    """Get meeting service instance."""
    return AgentMeetingService(session)


async def get_decision_service(
    session: AsyncSession = Depends(get_db_session),
) -> AgentDecisionService:
    """Get decision service instance."""
    return AgentDecisionService(session)


async def get_topic_analyzer(
    session: AsyncSession = Depends(get_db_session),
) -> TopicAnalyzer:
    """Get topic analyzer instance."""
    return TopicAnalyzer(session)


async def get_discussion_algorithm(
    session: AsyncSession = Depends(get_db_session),
    meeting_service: AgentMeetingService = Depends(get_meeting_service),
) -> SequentialDiscussionAlgorithm:
    """Get discussion algorithm instance."""
    return SequentialDiscussionAlgorithm(session, meeting_service)


# ============================================================================
# Communication Endpoints
# ============================================================================


@router.post(
    "/communications",
    response_model=CommunicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_communication(
    data: CommunicationCreate,
    service: AgentCommunicationService = Depends(get_communication_service),
) -> CommunicationResponse:
    """
    Log a communication between agents.

    Implements AC-COMM-001 from SPEC-AGENT-COMM-001.

    Args:
        data: Communication creation data
        service: Communication service (injected)

    Returns:
        The created communication record

    Raises:
        HTTPException: If message size exceeds limit
    """
    try:
        return await service.log_communication(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )


@router.get("/communications", response_model=CommunicationListResponse)
async def query_communications(
    sender_id: UUID | None = Query(None, description="Filter by sender agent ID"),
    receiver_id: UUID | None = Query(None, description="Filter by receiver agent ID"),
    topic: str | None = Query(None, description="Filter by topic"),
    start_date: datetime | None = Query(None, description="Start of date range"),
    end_date: datetime | None = Query(None, description="End of date range"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    service: AgentCommunicationService = Depends(get_communication_service),
) -> CommunicationListResponse:
    """
    Query communications with filters and pagination.

    Implements AC-COMM-002 from SPEC-AGENT-COMM-001.

    Args:
        sender_id: Optional sender filter
        receiver_id: Optional receiver filter
        topic: Optional topic filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        page: Page number
        page_size: Items per page
        service: Communication service (injected)

    Returns:
        Paginated list of communications
    """
    return await service.query_communications(
        sender_id=sender_id,
        receiver_id=receiver_id,
        topic=topic,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/communications/{communication_id}", response_model=CommunicationResponse)
async def get_communication(
    communication_id: UUID,
    service: AgentCommunicationService = Depends(get_communication_service),
) -> CommunicationResponse:
    """
    Get a specific communication by ID.

    Args:
        communication_id: Communication ID
        service: Communication service (injected)

    Returns:
        The communication record

    Raises:
        HTTPException: If communication not found
    """
    communication = await service.get_communication(communication_id)
    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Communication {communication_id} not found",
        )
    return communication


# ============================================================================
# Meeting Endpoints
# ============================================================================


@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingResponse:
    """
    Create a new meeting.

    Implements AC-MEET-001 from SPEC-AGENT-COMM-001.

    Args:
        data: Meeting creation data
        service: Meeting service (injected)

    Returns:
        The created meeting

    Raises:
        HTTPException: If participant list is invalid
    """
    try:
        return await service.create_meeting(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(
    meeting_id: UUID,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingDetailResponse:
    """
    Get detailed meeting information.

    Implements AC-MEET-003 from SPEC-AGENT-COMM-001.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        Detailed meeting information

    Raises:
        HTTPException: If meeting not found
    """
    meeting = await service.get_meeting_detail(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )
    return meeting


@router.post("/meetings/{meeting_id}/start", response_model=MeetingResponse)
async def start_meeting(
    meeting_id: UUID,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingResponse:
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


@router.post("/meetings/{meeting_id}/complete", response_model=MeetingResponse)
async def complete_meeting(
    meeting_id: UUID,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingResponse:
    """
    Complete a meeting.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        The updated meeting

    Raises:
        HTTPException: If meeting not found
    """
    meeting = await service.complete_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )
    return meeting


@router.get("/meetings/{meeting_id}/participants", response_model=list[MeetingParticipantResponse])
async def get_meeting_participants(
    meeting_id: UUID,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> list[MeetingParticipantResponse]:
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
    "/meetings/{meeting_id}/participants",
    response_model=MeetingParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_meeting_participant(
    meeting_id: UUID,
    agent_id: UUID,
    role: str = Query("participant", description="Participant role"),
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingParticipantResponse:
    """
    Add a participant to a meeting.

    Args:
        meeting_id: Meeting ID
        agent_id: Agent identifier
        role: Participant role
        service: Meeting service (injected)

    Returns:
        The added participant
    """
    return await service.add_participant(meeting_id, agent_id, role)


@router.get("/meetings/{meeting_id}/messages", response_model=list[MeetingMessageResponse])
async def get_meeting_messages(
    meeting_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    service: AgentMeetingService = Depends(get_meeting_service),
) -> list[MeetingMessageResponse]:
    """
    Get messages from a meeting.

    Args:
        meeting_id: Meeting ID
        limit: Maximum number of messages
        service: Meeting service (injected)

    Returns:
        List of meeting messages
    """
    return await service.get_messages(meeting_id, limit)


@router.post(
    "/meetings/{meeting_id}/messages",
    response_model=MeetingMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_meeting_message(
    meeting_id: UUID,
    data: MeetingMessageCreate,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingMessageResponse:
    """
    Record a message in a meeting.

    Args:
        meeting_id: Meeting ID
        data: Message creation data
        service: Meeting service (injected)

    Returns:
        The recorded message

    Raises:
        HTTPException: If recording fails
    """
    # Override meeting_id from URL
    data.meeting_id = meeting_id
    return await service.record_message(data)


@router.post("/meetings/{meeting_id}/next-round", response_model=MeetingResponse)
async def next_discussion_round(
    meeting_id: UUID,
    service: AgentMeetingService = Depends(get_meeting_service),
) -> MeetingResponse:
    """
    Move to the next discussion round.

    Args:
        meeting_id: Meeting ID
        service: Meeting service (injected)

    Returns:
        The updated meeting

    Raises:
        HTTPException: If meeting not found
    """
    meeting = await service.next_round(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found",
        )
    return meeting


# ============================================================================
# Decision Endpoints
# ============================================================================


@router.post("/decisions", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
async def record_decision(
    data: DecisionCreate,
    service: AgentDecisionService = Depends(get_decision_service),
) -> DecisionResponse:
    """
    Record a decision.

    Implements AC-DECISION-001 from SPEC-AGENT-COMM-001.

    Args:
        data: Decision creation data
        service: Decision service (injected)

    Returns:
        The recorded decision
    """
    return await service.record_decision(data)


@router.get("/decisions", response_model=DecisionListResponse)
async def query_decisions(
    meeting_id: UUID | None = Query(None, description="Filter by meeting ID"),
    start_date: datetime | None = Query(None, description="Start of date range"),
    end_date: datetime | None = Query(None, description="End of date range"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    service: AgentDecisionService = Depends(get_decision_service),
) -> DecisionListResponse:
    """
    Query decisions with filters and pagination.

    Implements AC-DECISION-002 from SPEC-AGENT-COMM-001.

    Args:
        meeting_id: Optional meeting filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        page: Page number
        page_size: Items per page
        service: Decision service (injected)

    Returns:
        Paginated list of decisions
    """
    return await service.query_decisions(
        meeting_id=meeting_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/decisions/{meeting_id}/meeting", response_model=list[DecisionResponse])
async def get_meeting_decisions(
    meeting_id: UUID,
    service: AgentDecisionService = Depends(get_decision_service),
) -> list[DecisionResponse]:
    """
    Get all decisions for a meeting.

    Args:
        meeting_id: Meeting ID
        service: Decision service (injected)

    Returns:
        List of decisions for the meeting
    """
    return await service.get_meeting_decisions(meeting_id)


# ============================================================================
# Topic Analysis Endpoints
# ============================================================================


@router.get("/topics/suggestions", response_model=TopicSuggestionResponse)
async def suggest_topics(
    agent_ids: str = Query(..., description="Comma-separated list of agent IDs"),
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    max_topics: int = Query(5, ge=1, le=10, description="Maximum topics to suggest"),
    analyzer: TopicAnalyzer = Depends(get_topic_analyzer),
) -> TopicSuggestionResponse:
    """
    Suggest meeting topics based on recent communications.

    Implements AC-TOPIC-002 from SPEC-AGENT-COMM-001.

    Args:
        agent_ids: Comma-separated list of agent IDs to analyze
        time_range_hours: Time range to analyze in hours
        max_topics: Maximum number of topics to suggest
        analyzer: Topic analyzer (injected)

    Returns:
        List of suggested topics
    """
    # Parse agent IDs
    agent_id_list = [UUID(aid.strip()) for aid in agent_ids.split(",") if aid.strip()]

    suggestions = await analyzer.suggest_topics(
        agent_ids=agent_id_list,
        time_range_hours=time_range_hours,
        max_topics=max_topics,
    )

    # Convert to response format
    suggested_topics = [
        SuggestedTopic(
            topic=s["topic"],
            priority=s["priority"],
            reason=s["reason"],
            related_communications=s["related_communications"],
        )
        for s in suggestions
    ]

    return TopicSuggestionResponse(
        suggested_topics=suggested_topics,
        time_range_hours=time_range_hours,
    )


__all__ = ["router"]
