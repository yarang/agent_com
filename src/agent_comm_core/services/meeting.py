"""
Meeting service for agent coordination and discussion.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from agent_comm_core.models.meeting import (
    Meeting,
    MeetingCreate,
    MeetingMessage,
    MeetingMessageCreate,
    MeetingParticipant,
    MeetingParticipantCreate,
    MeetingStatus,
)
from agent_comm_core.repositories.base import MeetingRepository


class MeetingService:
    """
    Service for managing meetings between agents.

    Provides methods for creating meetings, managing participants,
    recording messages, and controlling meeting state.
    """

    def __init__(self, repository: MeetingRepository) -> None:
        """
        Initialize the meeting service.

        Args:
            repository: Meeting repository instance
        """
        self._repository = repository

    async def create_meeting(
        self,
        title: str,
        participant_ids: list[str],
        description: Optional[str] = None,
        agenda: Optional[list[str]] = None,
        max_duration_seconds: Optional[int] = None,
    ) -> Meeting:
        """
        Create a new meeting.

        Args:
            title: Meeting title
            participant_ids: List of participant agent IDs
            description: Optional meeting description
            agenda: Optional list of agenda items
            max_duration_seconds: Optional maximum duration

        Returns:
            The created meeting

        Raises:
            ValueError: If participant_ids is empty or title is invalid
        """
        if not participant_ids:
            raise ValueError("At least one participant is required")

        create_data = MeetingCreate(
            title=title,
            description=description,
            agenda=agenda or [],
            max_duration_seconds=max_duration_seconds,
            participant_ids=participant_ids,
        )
        meeting = await self._repository.create(create_data)

        # Add all participants
        for agent_id in participant_ids:
            await self.add_participant(meeting.id, agent_id)

        return meeting

    async def get_meeting(self, id: UUID) -> Optional[Meeting]:
        """
        Retrieve a meeting by its ID.

        Args:
            id: Meeting ID

        Returns:
            Meeting if found, None otherwise
        """
        return await self._repository.get_by_id(id)

    async def start_meeting(self, id: UUID) -> Optional[Meeting]:
        """
        Start a meeting.

        Args:
            id: Meeting ID

        Returns:
            Updated meeting if found, None otherwise
        """
        meeting = await self._repository.update_status(id, MeetingStatus.ACTIVE)
        if meeting:
            await self._repository.update(id, {"started_at": datetime.utcnow()})
        return meeting

    async def end_meeting(self, id: UUID) -> Optional[Meeting]:
        """
        End a meeting.

        Args:
            id: Meeting ID

        Returns:
            Updated meeting if found, None otherwise
        """
        meeting = await self._repository.update_status(id, MeetingStatus.COMPLETED)
        if meeting:
            await self._repository.update(id, {"ended_at": datetime.utcnow()})
        return meeting

    async def add_participant(
        self, meeting_id: UUID, agent_id: str, role: str = "participant"
    ) -> MeetingParticipant:
        """
        Add a participant to a meeting.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent identifier
            role: Participant role (default: "participant")

        Returns:
            The created participant

        Raises:
            ValueError: If meeting is not found
        """
        create_data = MeetingParticipantCreate(meeting_id=meeting_id, agent_id=agent_id, role=role)
        return await self._repository.add_participant(create_data)

    async def get_participants(self, meeting_id: UUID) -> list[MeetingParticipant]:
        """
        Get all participants for a meeting.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of meeting participants
        """
        return await self._repository.get_participants(meeting_id)

    async def record_message(
        self,
        meeting_id: UUID,
        agent_id: str,
        content: str,
        message_type: str = "statement",
        in_reply_to: Optional[UUID] = None,
    ) -> MeetingMessage:
        """
        Record a message in a meeting.

        Args:
            meeting_id: Meeting ID
            agent_id: Agent identifier
            content: Message content
            message_type: Type of message (default: "statement")
            in_reply_to: Optional ID of message this replies to

        Returns:
            The created message

        Raises:
            ValueError: If meeting is not found or not active
        """
        meeting = await self._repository.get_by_id(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        if meeting.status != MeetingStatus.ACTIVE:
            raise ValueError(f"Cannot record message in meeting with status {meeting.status}")

        # Get next sequence number
        messages = await self._repository.get_messages(meeting_id, limit=1)
        next_sequence = (messages[0].sequence_number if messages else 0) + 1

        create_data = MeetingMessageCreate(
            meeting_id=meeting_id,
            agent_id=agent_id,
            content=content,
            message_type=message_type,
        )
        message = await self._repository.record_message(create_data)

        # Update sequence number
        await self._repository.update(
            type(message).id,  # type: ignore
            {"sequence_number": next_sequence, "in_reply_to": in_reply_to},
        )

        return message

    async def get_messages(self, meeting_id: UUID, limit: int = 100) -> list[MeetingMessage]:
        """
        Get messages from a meeting.

        Args:
            meeting_id: Meeting ID
            limit: Maximum number of messages

        Returns:
            List of meeting messages in sequence order
        """
        return await self._repository.get_messages(meeting_id, limit)

    async def get_meetings_by_status(self, status: MeetingStatus) -> list[Meeting]:
        """
        Get meetings by status.

        Args:
            status: Meeting status to filter by

        Returns:
            List of meetings with the given status
        """
        return await self._repository.get_by_status(status.value)
