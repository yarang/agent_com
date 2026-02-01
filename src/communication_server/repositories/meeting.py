"""
SQLAlchemy implementation of MeetingRepository.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.models.decision import Decision
from agent_comm_core.models.meeting import (
    Meeting,
    MeetingCreate,
    MeetingMessage,
    MeetingMessageCreate,
    MeetingParticipant,
    MeetingParticipantCreate,
)
from agent_comm_core.repositories.base import MeetingRepository

from communication_server.db.meeting import (
    DecisionDB,
    MeetingDB,
    MeetingMessageDB,
    MeetingParticipantDB,
)


class SQLALchemyMeetingRepository(MeetingRepository):
    """
    SQLAlchemy implementation of MeetingRepository.

    Provides CRUD operations for meetings, participants, and messages
    using PostgreSQL with asyncpg driver.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Meeting]:
        """
        Retrieve a meeting by its ID.

        Args:
            id: Unique identifier of the meeting

        Returns:
            The meeting if found, None otherwise
        """
        result = await self._session.execute(select(MeetingDB).where(MeetingDB.id == id))
        db_meeting = result.scalar_one_or_none()
        return db_meeting.to_pydantic() if db_meeting else None

    async def create(self, data: MeetingCreate) -> Meeting:
        """
        Create a new meeting.

        Args:
            data: Meeting creation data

        Returns:
            The created meeting
        """
        db_meeting = MeetingDB(
            title=data.title,
            description=data.description,
            agenda=data.agenda,
            max_duration_seconds=data.max_duration_seconds,
            status="pending",
        )
        self._session.add(db_meeting)
        await self._session.flush()
        return db_meeting.to_pydantic()

    async def update(self, id: UUID, data: dict) -> Optional[Meeting]:
        """
        Update an existing meeting.

        Args:
            id: Unique identifier of the meeting
            data: Fields to update

        Returns:
            The updated meeting if found, None otherwise
        """
        # Build update values, excluding None values
        update_values = {k: v for k, v in data.items() if v is not None}

        if not update_values:
            return await self.get_by_id(id)

        result = await self._session.execute(
            update(MeetingDB).where(MeetingDB.id == id).values(**update_values).returning(MeetingDB)
        )
        db_meeting = result.scalar_one_or_none()
        return db_meeting.to_pydantic() if db_meeting else None

    async def delete(self, id: UUID) -> bool:
        """
        Delete a meeting by its ID.

        Args:
            id: Unique identifier of the meeting

        Returns:
            True if deleted, False if not found
        """
        result = await self._session.execute(delete(MeetingDB).where(MeetingDB.id == id))
        return result.rowcount > 0

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Meeting]:
        """
        List all meetings with pagination.

        Args:
            limit: Maximum number of meetings to return
            offset: Number of meetings to skip

        Returns:
            List of meetings ordered by creation time (newest first)
        """
        result = await self._session.execute(
            select(MeetingDB).order_by(MeetingDB.created_at.desc()).limit(limit).offset(offset)
        )
        db_meetings = result.scalars().all()
        return [meeting.to_pydantic() for meeting in db_meetings]

    async def get_by_status(self, status: str) -> list[Meeting]:
        """
        Retrieve meetings by status.

        Args:
            status: Meeting status to filter by

        Returns:
            List of meetings with the given status
        """
        result = await self._session.execute(
            select(MeetingDB)
            .where(MeetingDB.status == status)
            .order_by(MeetingDB.created_at.desc())
        )
        db_meetings = result.scalars().all()
        return [meeting.to_pydantic() for meeting in db_meetings]

    async def add_participant(self, data: MeetingParticipantCreate) -> MeetingParticipant:
        """
        Add a participant to a meeting.

        Args:
            data: Participant creation data

        Returns:
            The created participant
        """
        db_participant = MeetingParticipantDB(
            meeting_id=data.meeting_id,
            agent_id=data.agent_id,
            role=data.role,
        )
        self._session.add(db_participant)
        await self._session.flush()
        return db_participant.to_pydantic()

    async def get_participants(self, meeting_id: UUID) -> list[MeetingParticipant]:
        """
        Get all participants for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of meeting participants
        """
        result = await self._session.execute(
            select(MeetingParticipantDB)
            .where(MeetingParticipantDB.meeting_id == meeting_id)
            .order_by(MeetingParticipantDB.joined_at.asc())
        )
        db_participants = result.scalars().all()
        return [p.to_pydantic() for p in db_participants]

    async def record_message(self, data: MeetingMessageCreate) -> MeetingMessage:
        """
        Record a message in a meeting.

        Args:
            data: Message creation data

        Returns:
            The created message
        """
        # Get next sequence number
        seq_result = await self._session.execute(
            select(MeetingMessageDB.sequence_number)
            .where(MeetingMessageDB.meeting_id == data.meeting_id)
            .order_by(MeetingMessageDB.sequence_number.desc())
            .limit(1)
        )
        last_seq = seq_result.scalar_one_or_none()
        next_sequence = (last_seq + 1) if last_seq is not None else 1

        db_message = MeetingMessageDB(
            meeting_id=data.meeting_id,
            agent_id=data.agent_id,
            content=data.content,
            message_type=data.message_type,
            sequence_number=next_sequence,
        )
        self._session.add(db_message)
        await self._session.flush()
        return db_message.to_pydantic()

    async def get_messages(self, meeting_id: UUID, limit: int = 100) -> list[MeetingMessage]:
        """
        Get messages from a meeting.

        Args:
            meeting_id: Meeting ID
            limit: Maximum number of messages

        Returns:
            List of meeting messages in sequence order
        """
        result = await self._session.execute(
            select(MeetingMessageDB)
            .where(MeetingMessageDB.meeting_id == meeting_id)
            .order_by(MeetingMessageDB.sequence_number.asc())
            .limit(limit)
        )
        db_messages = result.scalars().all()
        return [msg.to_pydantic() for msg in db_messages]

    async def update_status(self, meeting_id: UUID, status: str) -> Optional[Meeting]:
        """
        Update the status of a meeting.

        Args:
            meeting_id: Meeting ID
            status: New status

        Returns:
            Updated meeting if found, None otherwise
        """
        update_data: dict[str, object] = {"status": status}

        # Update timestamps based on status
        if status == "active":
            update_data["started_at"] = datetime.utcnow()
        elif status in ("completed", "cancelled"):
            update_data["ended_at"] = datetime.utcnow()

        result = await self._session.execute(
            update(MeetingDB)
            .where(MeetingDB.id == meeting_id)
            .values(**update_data)
            .returning(MeetingDB)
        )
        db_meeting = result.scalar_one_or_none()
        return db_meeting.to_pydantic() if db_meeting else None
