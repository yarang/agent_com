"""
Repository layer for chat room operations.

Provides data access methods for chat rooms, participants, and messages.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.chat import (
    ChatMessageDB,
    ChatParticipantDB,
    ChatRoomDB,
    SenderType,
)
from agent_comm_core.models.chat import (
    ChatRoomUpdate,
)


class ChatRepository:
    """
    Repository for chat room operations.

    Handles CRUD operations for chat rooms, participants, and messages.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with a database session.

        Args:
            session: Async database session
        """
        self.session = session

    # ========================================================================
    # Chat Room Operations
    # ========================================================================

    async def create_room(
        self, project_id: UUID, name: str, description: str | None, created_by: UUID
    ) -> ChatRoomDB:
        """
        Create a new chat room.

        Args:
            project_id: Project UUID
            name: Room name
            description: Optional description
            created_by: Creator user UUID

        Returns:
            Created chat room
        """
        room = ChatRoomDB(
            project_id=project_id,
            name=name,
            description=description,
            created_by=created_by,
        )
        self.session.add(room)
        await self.session.flush()
        return room

    async def get_room(self, room_id: UUID) -> ChatRoomDB | None:
        """
        Get a chat room by ID.

        Args:
            room_id: Room UUID

        Returns:
            Chat room if found, None otherwise
        """
        result = await self.session.execute(select(ChatRoomDB).where(ChatRoomDB.id == room_id))
        return result.scalar_one_or_none()

    async def list_rooms(
        self, project_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[ChatRoomDB]:
        """
        List chat rooms with optional filtering.

        Args:
            project_id: Optional project filter
            limit: Maximum number of rooms
            offset: Number of rooms to skip

        Returns:
            List of chat rooms
        """
        stmt = select(ChatRoomDB)
        if project_id:
            stmt = stmt.where(ChatRoomDB.project_id == project_id)
        stmt = stmt.order_by(ChatRoomDB.updated_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_room(self, room_id: UUID, updates: ChatRoomUpdate) -> ChatRoomDB | None:
        """
        Update a chat room.

        Args:
            room_id: Room UUID
            updates: Fields to update

        Returns:
            Updated room if found, None otherwise
        """
        room = await self.get_room(room_id)
        if not room:
            return None
        if updates.name is not None:
            room.name = updates.name
        if updates.description is not None:
            room.description = updates.description
        await self.session.flush()
        return room

    async def delete_room(self, room_id: UUID) -> bool:
        """
        Delete a chat room.

        Args:
            room_id: Room UUID

        Returns:
            True if deleted, False if not found
        """
        room = await self.get_room(room_id)
        if not room:
            return False
        await self.session.delete(room)
        return True

    async def get_room_participant_count(self, room_id: UUID) -> int:
        """
        Get the number of participants in a room.

        Args:
            room_id: Room UUID

        Returns:
            Participant count
        """
        result = await self.session.execute(
            select(func.count(ChatParticipantDB.id)).where(ChatParticipantDB.room_id == room_id)
        )
        return result.scalar() or 0

    async def get_room_message_count(self, room_id: UUID) -> int:
        """
        Get the number of messages in a room.

        Args:
            room_id: Room UUID

        Returns:
            Message count
        """
        result = await self.session.execute(
            select(func.count(ChatMessageDB.id)).where(ChatMessageDB.room_id == room_id)
        )
        return result.scalar() or 0

    # ========================================================================
    # Participant Operations
    # ========================================================================

    async def add_participant(
        self, room_id: UUID, agent_id: UUID | None = None, user_id: UUID | None = None
    ) -> ChatParticipantDB:
        """
        Add a participant to a chat room.

        Args:
            room_id: Room UUID
            agent_id: Optional agent UUID
            user_id: Optional user UUID

        Returns:
            Created participant
        """
        participant = ChatParticipantDB(room_id=room_id, agent_id=agent_id, user_id=user_id)
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def get_participants(self, room_id: UUID) -> list[ChatParticipantDB]:
        """
        Get all participants in a room.

        Args:
            room_id: Room UUID

        Returns:
            List of participants
        """
        result = await self.session.execute(
            select(ChatParticipantDB).where(ChatParticipantDB.room_id == room_id)
        )
        return list(result.scalars().all())

    async def remove_participant(self, participant_id: UUID) -> bool:
        """
        Remove a participant from a room.

        Args:
            participant_id: Participant UUID

        Returns:
            True if removed, False if not found
        """
        result = await self.session.execute(
            select(ChatParticipantDB).where(ChatParticipantDB.id == participant_id)
        )
        participant = result.scalar_one_or_none()
        if not participant:
            return False
        await self.session.delete(participant)
        return True

    async def is_participant(
        self, room_id: UUID, user_id: UUID | None = None, agent_id: UUID | None = None
    ) -> bool:
        """
        Check if a user or agent is a participant in a room.

        Args:
            room_id: Room UUID
            user_id: Optional user UUID to check
            agent_id: Optional agent UUID to check

        Returns:
            True if participant, False otherwise
        """
        if user_id:
            result = await self.session.execute(
                select(ChatParticipantDB).where(
                    ChatParticipantDB.room_id == room_id,
                    ChatParticipantDB.user_id == user_id,
                )
            )
        else:
            result = await self.session.execute(
                select(ChatParticipantDB).where(
                    ChatParticipantDB.room_id == room_id,
                    ChatParticipantDB.agent_id == agent_id,
                )
            )
        return result.scalar_one_or_none() is not None

    # ========================================================================
    # Message Operations
    # ========================================================================

    async def create_message(
        self,
        room_id: UUID,
        sender_type: SenderType,
        sender_id: UUID,
        content: str,
        message_type: str,
        metadata: dict | None = None,
    ) -> ChatMessageDB:
        """
        Create a new chat message.

        Args:
            room_id: Room UUID
            sender_type: Sender type (user or agent)
            sender_id: Sender UUID
            content: Message content
            message_type: Message type
            metadata: Optional metadata

        Returns:
            Created message
        """
        message = ChatMessageDB(
            room_id=room_id,
            sender_type=sender_type.value,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            metadata=metadata,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_messages(
        self, room_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ChatMessageDB]:
        """
        Get messages from a room with pagination.

        Args:
            room_id: Room UUID
            limit: Maximum number of messages
            offset: Number of messages to skip

        Returns:
            List of messages ordered by creation time
        """
        stmt = (
            select(ChatMessageDB)
            .where(ChatMessageDB.room_id == room_id)
            .order_by(ChatMessageDB.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        # Reverse to get chronological order
        return list(reversed(messages))

    async def get_message_count(self, room_id: UUID) -> int:
        """
        Get the total number of messages in a room.

        Args:
            room_id: Room UUID

        Returns:
            Message count
        """
        result = await self.session.execute(
            select(func.count(ChatMessageDB.id)).where(ChatMessageDB.room_id == room_id)
        )
        return result.scalar() or 0
