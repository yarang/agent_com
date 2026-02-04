"""
Repository implementations for SPEC-AGENT-COMM-001.

Provides SQLAlchemy-based repository implementations for the database models
defined in SPEC-AGENT-COMM-001.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.agent_comm import (
    CommunicationCreate,
    CommunicationResponse,
    DecisionCreate,
    DecisionResponse,
    MeetingCreate,
    MeetingMessageCreate,
    MeetingMessageResponse,
    MeetingParticipantCreate,
    MeetingParticipantResponse,
    MeetingResponse,
)
from communication_server.db.agent_comm import (
    AgentCommunicationDB,
    AgentDecisionDB,
    AgentMeetingDB,
    AgentMeetingMessageDB,
    AgentMeetingParticipantDB,
    MeetingStatus,
)


class AgentCommunicationRepository:
    """
    Repository for agent communications.

    Provides CRUD operations for the AgentCommunicationDB model.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, data: CommunicationCreate) -> CommunicationResponse:
        """
        Create a new communication.

        Args:
            data: Communication creation data

        Returns:
            The created communication
        """
        db_comm = AgentCommunicationDB(
            sender_id=data.sender_id,
            receiver_id=data.receiver_id,
            message_content=data.message_content,
            topic=data.topic,
        )
        self._session.add(db_comm)
        await self._session.flush()

        return CommunicationResponse(
            id=db_comm.id,
            timestamp=db_comm.timestamp,
            sender_id=db_comm.sender_id,
            receiver_id=db_comm.receiver_id,
            message_content=db_comm.message_content,
            topic=db_comm.topic,
            created_at=db_comm.created_at,
        )

    async def get_by_id(self, id: UUID) -> CommunicationResponse | None:
        """
        Retrieve a communication by its ID.

        Args:
            id: Unique identifier of the communication

        Returns:
            The communication if found, None otherwise
        """
        result = await self._session.execute(
            select(AgentCommunicationDB).where(AgentCommunicationDB.id == id)
        )
        db_comm = result.scalar_one_or_none()
        if not db_comm:
            return None

        return CommunicationResponse(
            id=db_comm.id,
            timestamp=db_comm.timestamp,
            sender_id=db_comm.sender_id,
            receiver_id=db_comm.receiver_id,
            message_content=db_comm.message_content,
            topic=db_comm.topic,
            created_at=db_comm.created_at,
        )

    async def list_with_filters(
        self,
        sender_id: UUID | None = None,
        receiver_id: UUID | None = None,
        topic: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[CommunicationResponse], int]:
        """
        List communications with optional filters.

        Args:
            sender_id: Optional sender filter
            receiver_id: Optional receiver filter
            topic: Optional topic filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of communications, total count)
        """
        conditions = []

        if sender_id:
            conditions.append(AgentCommunicationDB.sender_id == sender_id)
        if receiver_id:
            conditions.append(AgentCommunicationDB.receiver_id == receiver_id)
        if topic:
            conditions.append(AgentCommunicationDB.topic == topic)
        if start_date:
            conditions.append(AgentCommunicationDB.timestamp >= start_date)
        if end_date:
            conditions.append(AgentCommunicationDB.timestamp <= end_date)

        # Build query
        query = select(AgentCommunicationDB)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(AgentCommunicationDB.timestamp.desc())

        # Get total count
        count_query = select(func.count()).select_from(query.alias())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        result = await self._session.execute(query.limit(limit).offset(offset))
        db_comms = result.scalars().all()

        communications = [
            CommunicationResponse(
                id=c.id,
                timestamp=c.timestamp,
                sender_id=c.sender_id,
                receiver_id=c.receiver_id,
                message_content=c.message_content,
                topic=c.topic,
                created_at=c.created_at,
            )
            for c in db_comms
        ]

        return communications, total


class AgentMeetingRepository:
    """
    Repository for agent meetings.

    Provides CRUD operations for the AgentMeetingDB model and related models.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create_meeting(self, data: MeetingCreate) -> MeetingResponse:
        """
        Create a new meeting.

        Args:
            data: Meeting creation data

        Returns:
            The created meeting
        """
        db_meeting = AgentMeetingDB(
            topic=data.topic,
            meeting_type=data.meeting_type,
            max_discussion_rounds=data.max_discussion_rounds,
            status=MeetingStatus.PENDING,
        )
        self._session.add(db_meeting)
        await self._session.flush()

        # Add participants
        for order, agent_id in enumerate(data.participant_ids, start=1):
            participant = AgentMeetingParticipantDB(
                meeting_id=db_meeting.id,
                agent_id=agent_id,
                role="moderator" if order == 1 else "participant",
                speaking_order=order,
            )
            self._session.add(participant)

        await self._session.flush()

        return MeetingResponse(
            id=db_meeting.id,
            topic=db_meeting.topic,
            meeting_type=db_meeting.meeting_type,
            status=db_meeting.status,
            created_at=db_meeting.created_at,
            started_at=db_meeting.started_at,
            completed_at=db_meeting.completed_at,
            max_discussion_rounds=db_meeting.max_discussion_rounds,
            current_round=db_meeting.current_round,
        )

    async def get_by_id(self, id: UUID) -> MeetingResponse | None:
        """
        Retrieve a meeting by its ID.

        Args:
            id: Unique identifier of the meeting

        Returns:
            The meeting if found, None otherwise
        """
        result = await self._session.execute(select(AgentMeetingDB).where(AgentMeetingDB.id == id))
        db_meeting = result.scalar_one_or_none()
        if not db_meeting:
            return None

        return MeetingResponse(
            id=db_meeting.id,
            topic=db_meeting.topic,
            meeting_type=db_meeting.meeting_type,
            status=db_meeting.status,
            created_at=db_meeting.created_at,
            started_at=db_meeting.started_at,
            completed_at=db_meeting.completed_at,
            max_discussion_rounds=db_meeting.max_discussion_rounds,
            current_round=db_meeting.current_round,
        )

    async def update_status(
        self,
        meeting_id: UUID,
        status: MeetingStatus,
    ) -> MeetingResponse | None:
        """
        Update the status of a meeting.

        Args:
            meeting_id: Meeting ID
            status: New status

        Returns:
            Updated meeting if found, None otherwise
        """
        update_data: dict = {"status": status}

        # Update timestamps based on status
        if status == MeetingStatus.IN_PROGRESS:
            update_data["started_at"] = datetime.utcnow()
        elif status in (MeetingStatus.COMPLETED, MeetingStatus.FAILED):
            update_data["completed_at"] = datetime.utcnow()

        result = await self._session.execute(
            update(AgentMeetingDB)
            .where(AgentMeetingDB.id == meeting_id)
            .values(**update_data)
            .returning(AgentMeetingDB)
        )
        db_meeting = result.scalar_one_or_none()
        if not db_meeting:
            return None

        return MeetingResponse(
            id=db_meeting.id,
            topic=db_meeting.topic,
            meeting_type=db_meeting.meeting_type,
            status=db_meeting.status,
            created_at=db_meeting.created_at,
            started_at=db_meeting.started_at,
            completed_at=db_meeting.completed_at,
            max_discussion_rounds=db_meeting.max_discussion_rounds,
            current_round=db_meeting.current_round,
        )

    async def increment_round(self, meeting_id: UUID) -> MeetingResponse | None:
        """
        Increment the current discussion round.

        Args:
            meeting_id: Meeting ID

        Returns:
            Updated meeting if found, None otherwise
        """
        result = await self._session.execute(
            update(AgentMeetingDB)
            .where(AgentMeetingDB.id == meeting_id)
            .values(current_round=AgentMeetingDB.current_round + 1)
            .returning(AgentMeetingDB)
        )
        db_meeting = result.scalar_one_or_none()
        if not db_meeting:
            return None

        return MeetingResponse(
            id=db_meeting.id,
            topic=db_meeting.topic,
            meeting_type=db_meeting.meeting_type,
            status=db_meeting.status,
            created_at=db_meeting.created_at,
            started_at=db_meeting.started_at,
            completed_at=db_meeting.completed_at,
            max_discussion_rounds=db_meeting.max_discussion_rounds,
            current_round=db_meeting.current_round,
        )

    async def get_participants(
        self,
        meeting_id: UUID,
    ) -> list[MeetingParticipantResponse]:
        """
        Get all participants for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of meeting participants
        """
        result = await self._session.execute(
            select(AgentMeetingParticipantDB)
            .where(AgentMeetingParticipantDB.meeting_id == meeting_id)
            .order_by(AgentMeetingParticipantDB.speaking_order.asc())
        )
        db_participants = result.scalars().all()

        return [
            MeetingParticipantResponse(
                id=p.id,
                meeting_id=p.meeting_id,
                agent_id=p.agent_id,
                role=p.role,
                speaking_order=p.speaking_order,
                joined_at=p.created_at,
            )
            for p in db_participants
        ]

    async def add_participant(
        self,
        meeting_id: UUID,
        data: MeetingParticipantCreate,
    ) -> MeetingParticipantResponse:
        """
        Add a participant to a meeting.

        Args:
            meeting_id: Meeting ID
            data: Participant creation data

        Returns:
            The created participant
        """
        # Get next speaking order
        seq_result = await self._session.execute(
            select(func.max(AgentMeetingParticipantDB.speaking_order)).where(
                AgentMeetingParticipantDB.meeting_id == meeting_id
            )
        )
        last_order = seq_result.scalar_one_or_none()
        next_order = (last_order + 1) if last_order is not None else 1

        db_participant = AgentMeetingParticipantDB(
            meeting_id=meeting_id,
            agent_id=data.agent_id,
            role=data.role,
            speaking_order=next_order,
        )
        self._session.add(db_participant)
        await self._session.flush()

        return MeetingParticipantResponse(
            id=db_participant.id,
            meeting_id=db_participant.meeting_id,
            agent_id=db_participant.agent_id,
            role=db_participant.role,
            speaking_order=db_participant.speaking_order,
            joined_at=db_participant.created_at,
        )

    async def get_messages(
        self,
        meeting_id: UUID,
        limit: int = 100,
    ) -> list[MeetingMessageResponse]:
        """
        Get messages from a meeting.

        Args:
            meeting_id: Meeting ID
            limit: Maximum number of messages

        Returns:
            List of meeting messages in sequence order
        """
        result = await self._session.execute(
            select(AgentMeetingMessageDB)
            .where(AgentMeetingMessageDB.meeting_id == meeting_id)
            .order_by(AgentMeetingMessageDB.sequence_number.asc())
            .limit(limit)
        )
        db_messages = result.scalars().all()

        return [
            MeetingMessageResponse(
                id=m.id,
                meeting_id=m.meeting_id,
                agent_id=m.agent_id,
                message_content=m.message_content,
                message_type=m.message_type,
                sequence_number=m.sequence_number,
                timestamp=m.timestamp,
            )
            for m in db_messages
        ]

    async def create_message(
        self,
        data: MeetingMessageCreate,
    ) -> MeetingMessageResponse:
        """
        Record a message in a meeting.

        Args:
            data: Message creation data

        Returns:
            The created message
        """
        # Get next sequence number
        seq_result = await self._session.execute(
            select(func.max(AgentMeetingMessageDB.sequence_number)).where(
                AgentMeetingMessageDB.meeting_id == data.meeting_id
            )
        )
        last_seq = seq_result.scalar_one_or_none()
        next_sequence = (last_seq + 1) if last_seq is not None else 1

        db_message = AgentMeetingMessageDB(
            meeting_id=data.meeting_id,
            agent_id=data.agent_id,
            message_content=data.message_content,
            message_type=data.message_type,
            sequence_number=next_sequence,
        )
        self._session.add(db_message)
        await self._session.flush()

        return MeetingMessageResponse(
            id=db_message.id,
            meeting_id=db_message.meeting_id,
            agent_id=db_message.agent_id,
            message_content=db_message.message_content,
            message_type=db_message.message_type,
            sequence_number=db_message.sequence_number,
            timestamp=db_message.timestamp,
        )


class AgentDecisionRepository:
    """
    Repository for agent decisions.

    Provides CRUD operations for the AgentDecisionDB model.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, data: DecisionCreate) -> DecisionResponse:
        """
        Create a new decision.

        Args:
            data: Decision creation data

        Returns:
            The created decision
        """
        db_decision = AgentDecisionDB(
            meeting_id=data.meeting_id,
            decision_content=data.decision_content,
            rationale=data.rationale,
            related_communication_ids=data.related_communication_ids,
            participant_agreement=data.participant_agreement,
        )
        self._session.add(db_decision)
        await self._session.flush()

        return DecisionResponse(
            id=db_decision.id,
            meeting_id=db_decision.meeting_id,
            decision_content=db_decision.decision_content,
            rationale=db_decision.rationale,
            related_communication_ids=db_decision.related_communication_ids,
            participant_agreement=db_decision.participant_agreement,
            created_at=db_decision.created_at,
        )

    async def get_by_meeting(self, meeting_id: UUID) -> list[DecisionResponse]:
        """
        Get all decisions for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of decisions for the meeting
        """
        result = await self._session.execute(
            select(AgentDecisionDB)
            .where(AgentDecisionDB.meeting_id == meeting_id)
            .order_by(AgentDecisionDB.created_at.desc())
        )
        db_decisions = result.scalars().all()

        return [
            DecisionResponse(
                id=d.id,
                meeting_id=d.meeting_id,
                decision_content=d.decision_content,
                rationale=d.rationale,
                related_communication_ids=d.related_communication_ids,
                participant_agreement=d.participant_agreement,
                created_at=d.created_at,
            )
            for d in db_decisions
        ]

    async def list_with_filters(
        self,
        meeting_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DecisionResponse], int]:
        """
        List decisions with optional filters.

        Args:
            meeting_id: Optional meeting filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of decisions, total count)
        """
        conditions = []

        if meeting_id:
            conditions.append(AgentDecisionDB.meeting_id == meeting_id)
        if start_date:
            conditions.append(AgentDecisionDB.created_at >= start_date)
        if end_date:
            conditions.append(AgentDecisionDB.created_at <= end_date)

        # Build query
        query = select(AgentDecisionDB)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(AgentDecisionDB.created_at.desc())

        # Get total count
        count_query = select(func.count()).select_from(query.alias())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        result = await self._session.execute(query.limit(limit).offset(offset))
        db_decisions = result.scalars().all()

        decisions = [
            DecisionResponse(
                id=d.id,
                meeting_id=d.meeting_id,
                decision_content=d.decision_content,
                rationale=d.rationale,
                related_communication_ids=d.related_communication_ids,
                participant_agreement=d.participant_agreement,
                created_at=d.created_at,
            )
            for d in db_decisions
        ]

        return decisions, total


__all__ = [
    "AgentCommunicationRepository",
    "AgentMeetingRepository",
    "AgentDecisionRepository",
]
