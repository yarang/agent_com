"""
SQLAlchemy base model with common fields.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common fields and conventions:
    - id: UUID primary key
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.

        Converts CamelCase to snake_case and adds 's' if not already plural.
        """
        name = cls.__name__
        # Convert CamelCase to snake_case
        result = []
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                result.append("_")
            result.append(c.lower())
        table_name = "".join(result)

        # Add 's' if not ending with 's' (simple pluralization)
        if not table_name.endswith("s"):
            table_name += "s"

        return table_name

    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        return f"<{class_name}(id={self.id})>"
