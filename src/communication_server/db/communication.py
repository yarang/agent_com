"""
SQLAlchemy ORM model for communications.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from agent_comm_core.db.base import Base


class CommunicationDirection(str, Enum):
    """Direction of communication."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class CommunicationDB(Base):
    """
    SQLAlchemy ORM model for communications.

    Maps to the Communication Pydantic model in agent_comm_core.
    """

    __tablename__ = "communications"

    from_agent: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    to_agent: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[CommunicationDirection] = mapped_column(
        SQLEnum(CommunicationDirection),
        default=CommunicationDirection.INTERNAL,
        nullable=False,
        index=True,
    )
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    # JSON stored as text (PostgreSQL JSONB would be better but keeping simple)
    # Note: 'metadata' is reserved in SQLAlchemy, so we use 'meta_data'
    # Use name='metadata' to keep the database column name
    meta_data: Mapped[str] = mapped_column("metadata", Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def to_pydantic(self):
        """Convert to Pydantic model."""
        import json

        from agent_comm_core.models.communication import (
            Communication,
            CommunicationDirection,
        )

        return Communication(
            id=self.id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            message_type=self.message_type,
            content=self.content,
            direction=CommunicationDirection(self.direction.value),
            correlation_id=self.correlation_id,
            metadata=(
                json.loads(self.meta_data) if isinstance(self.meta_data, str) else self.meta_data
            ),
            created_at=self.created_at,
        )

    @classmethod
    def from_pydantic(cls, data):
        """Create from Pydantic model."""
        import json

        return cls(
            from_agent=data.from_agent,
            to_agent=data.to_agent,
            message_type=data.message_type,
            content=data.content,
            direction=CommunicationDirection(data.direction.value),
            correlation_id=data.correlation_id,
            meta_data=json.dumps(data.metadata) if data.metadata else "{}",
        )
