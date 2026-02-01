"""
API endpoints for decision management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.decision import Decision, DecisionCreate, DecisionStatus

from communication_server.dependencies import get_db_session
from communication_server.db.meeting import DecisionDB


router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[Decision])
async def list_decisions(
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting ID"),
    status: Optional[DecisionStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_db_session),
) -> list[Decision]:
    """
    List decisions with optional filtering.

    Args:
        meeting_id: Optional meeting ID filter
        status: Optional status filter
        limit: Maximum number of results
        session: Database session (injected)

    Returns:
        List of decisions
    """
    query = select(DecisionDB).order_by(DecisionDB.created_at.desc())

    if meeting_id:
        query = query.where(DecisionDB.meeting_id == meeting_id)
    if status:
        query = query.where(DecisionDB.status == status.value)

    query = query.limit(limit)

    result = await session.execute(query)
    db_decisions = result.scalars().all()
    return [d.to_pydantic() for d in db_decisions]


@router.get("/{decision_id}", response_model=Decision)
async def get_decision(
    decision_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Decision:
    """
    Get a specific decision by ID.

    Args:
        decision_id: Decision ID
        session: Database session (injected)

    Returns:
        The decision record

    Raises:
        HTTPException: If decision not found
    """
    result = await session.execute(select(DecisionDB).where(DecisionDB.id == decision_id))
    db_decision = result.scalar_one_or_none()

    if not db_decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    return db_decision.to_pydantic()


@router.post("", response_model=Decision, status_code=status.HTTP_201_CREATED)
async def create_decision(
    data: DecisionCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Decision:
    """
    Create a new decision.

    Args:
        data: Decision creation data
        session: Database session (injected)

    Returns:
        The created decision
    """
    try:
        db_decision = DecisionDB(
            title=data.title,
            description=data.description,
            context=data.context,
            proposed_by=data.proposed_by,
            options=data.options,
            status=DecisionStatus.PENDING.value,
            meeting_id=data.meeting_id,
        )
        session.add(db_decision)
        await session.flush()
        return db_decision.to_pydantic()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{decision_id}/vote", response_model=Decision)
async def vote_on_decision(
    decision_id: UUID,
    selected_option_title: str,
    rationale: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
) -> Decision:
    """
    Record a vote on a decision.

    Args:
        decision_id: Decision ID
        selected_option_title: Title of the selected option
        rationale: Optional rationale for the decision
        session: Database session (injected)

    Returns:
        The updated decision

    Raises:
        HTTPException: If decision not found or option invalid
    """
    result = await session.execute(select(DecisionDB).where(DecisionDB.id == decision_id))
    db_decision = result.scalar_one_or_none()

    if not db_decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Find the selected option
    selected_option = None
    for option in db_decision.options:
        if option.get("title") == selected_option_title:
            selected_option = option
            break

    if not selected_option:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option '{selected_option_title}' not found",
        )

    # Update decision
    db_decision.selected_option = selected_option
    db_decision.rationale = rationale
    db_decision.status = DecisionStatus.APPROVED.value

    from datetime import datetime

    db_decision.decided_at = datetime.utcnow()

    await session.flush()
    return db_decision.to_pydantic()
