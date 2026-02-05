"""
Generic SQLAlchemy repository base class.

This module provides a reusable base repository implementation that eliminates
code duplication across all SQLAlchemy-based repositories. It implements the
repository pattern with common CRUD operations and can be extended for
entity-specific operations.
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import ScalarResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from agent_comm_core.models.common import DEFAULT_LIST_LIMIT, DEFAULT_LIST_OFFSET, MAX_LIST_LIMIT

# Type variables for generic repository
ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class SQLAlchemyRepositoryBase(Generic[ModelType]):
    """
    Generic base repository for SQLAlchemy models.

    Provides standard CRUD operations that work with any SQLAlchemy model.
    Reduces code duplication by providing common database access patterns.

    Type Args:
        ModelType: The SQLAlchemy model class (must inherit from DeclarativeBase)

    Example:
        class UserRepository(SQLAlchemyRepositoryBase[UserDB]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, UserDB)

            # Additional methods specific to UserDB
            async def get_by_email(self, email: str) -> UserDB | None:
                result = await self._session.execute(
                    select(self._model).where(self._model.email == email)
                )
                return result.scalar_one_or_none()
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
            model: The SQLAlchemy model class this repository manages
        """
        self._session = session
        self._model = model

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def get_by_id(self, id: Any) -> ModelType | None:
        """
        Retrieve an entity by its ID.

        Args:
            id: Primary key value

        Returns:
            The entity if found, None otherwise
        """
        result = await self._session.execute(select(self._model).where(self._model.id == id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[Any]) -> list[ModelType]:
        """
        Retrieve multiple entities by their IDs.

        Args:
            ids: List of primary key values

        Returns:
            List of entities (only those found)
        """
        if not ids:
            return []
        result = await self._session.execute(select(self._model).where(self._model.id.in_(ids)))
        return list(result.scalars().all())

    async def exists(self, id: Any) -> bool:
        """
        Check if an entity exists by its ID.

        Args:
            id: Primary key value

        Returns:
            True if entity exists, False otherwise
        """
        result = await self._session.execute(
            select(self._model.id).where(self._model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none() is not None

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count entities with optional filters.

        Args:
            filters: Optional dictionary of field names to values for filtering

        Returns:
            Count of matching entities
        """
        from sqlalchemy import func

        query = select(func.count(self._model.id))  # type: ignore[attr-defined]

        if filters:
            for key, value in filters.items():
                if hasattr(self._model, key):
                    query = query.where(getattr(self._model, key) == value)

        result = await self._session.execute(query)
        return result.scalar() or 0

    async def list_all(
        self,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = DEFAULT_LIST_OFFSET,
        order_by: str | None = None,
        descending: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> ScalarResult[ModelType]:
        """
        List all entities with pagination and optional filtering.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            order_by: Field name to order by (default: created_at)
            descending: Sort order (True = descending)
            filters: Optional dictionary of field names to values for filtering

        Returns:
            Scalar result of entities

        Raises:
            ValueError: If limit exceeds MAX_LIST_LIMIT
        """
        if limit > MAX_LIST_LIMIT:
            raise ValueError(f"Limit {limit} exceeds maximum {MAX_LIST_LIMIT}")

        query = select(self._model)

        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if hasattr(self._model, key):
                    query = query.where(getattr(self._model, key) == value)

        # Apply ordering
        order_field = self._get_order_field(order_by)
        if descending:
            query = query.order_by(order_field.desc())
        else:
            query = query.order_by(order_field)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return result.scalars()

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new entity.

        Args:
            **kwargs: Field names and values for the new entity

        Returns:
            The created entity

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields (id, created_at, updated_at are auto-generated)
        entity = self._model(**kwargs)
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def create_many(self, entities_data: list[dict[str, Any]]) -> list[ModelType]:
        """
        Create multiple entities in a single operation.

        Args:
            entities_data: List of dictionaries containing entity data

        Returns:
            List of created entities
        """
        entities = [self._model(**data) for data in entities_data]
        self._session.add_all(entities)
        await self._session.flush()
        return entities

    async def update(self, id: Any, **kwargs: Any) -> ModelType | None:
        """
        Update an entity by its ID.

        Args:
            id: Primary key value
            **kwargs: Field names and values to update

        Returns:
            The updated entity if found, None otherwise
        """
        # Automatically update updated_at timestamp if it exists
        update_values = dict(kwargs)
        if hasattr(self._model, "updated_at") and "updated_at" not in update_values:
            update_values["updated_at"] = datetime.now(UTC)

        result = await self._session.execute(
            update(self._model).where(self._model.id == id).values(**update_values)
        )

        if result.rowcount == 0:
            return None

        return await self.get_by_id(id)

    async def update_many(
        self, ids: list[Any], **kwargs: Any
    ) -> int:
        """
        Update multiple entities by their IDs.

        Args:
            ids: List of primary key values
            **kwargs: Field names and values to update

        Returns:
            Number of entities updated
        """
        if not ids:
            return 0

        # Automatically update updated_at timestamp if it exists
        update_values = dict(kwargs)
        if hasattr(self._model, "updated_at") and "updated_at" not in update_values:
            update_values["updated_at"] = datetime.now(UTC)

        result = await self._session.execute(
            update(self._model).where(self._model.id.in_(ids)).values(**update_values)
        )
        await self._session.flush()
        return result.rowcount

    async def delete(self, id: Any) -> bool:
        """
        Delete an entity by its ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        result = await self._session.execute(delete(self._model).where(self._model.id == id))
        await self._session.flush()
        return result.rowcount > 0

    async def delete_many(self, ids: list[Any]) -> int:
        """
        Delete multiple entities by their IDs.

        Args:
            ids: List of primary key values

        Returns:
            Number of entities deleted
        """
        if not ids:
            return 0

        result = await self._session.execute(delete(self._model).where(self._model.id.in_(ids)))
        await self._session.flush()
        return result.rowcount

    async def soft_delete(self, id: Any) -> ModelType | None:
        """
        Soft delete an entity by setting status to deleted.

        Args:
            id: Primary key value

        Returns:
            The updated entity if found, None otherwise
        """
        if not hasattr(self._model, "status"):
            raise AttributeError(f"Model {self._model.__name__} does not have a 'status' field")

        return await self.update(id, status="deleted")

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    async def refresh(self, entity: ModelType) -> ModelType:
        """
        Refresh an entity from the database.

        Args:
            entity: The entity to refresh

        Returns:
            The refreshed entity
        """
        await self._session.refresh(entity)
        return entity

    async def expire(self, entity: ModelType) -> None:
        """
        Expire an entity's attributes so they are refreshed on next access.

        Args:
            entity: The entity to expire
        """
        self._session.expire(entity)

    async def merge(self, entity: ModelType) -> ModelType:
        """
        Merge a detached entity into the session.

        Args:
            entity: The detached entity to merge

        Returns:
            The merged entity
        """
        return await self._session.merge(entity)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_order_field(self, field_name: str | None) -> Any:
        """
        Get the model field for ordering.

        Args:
            field_name: Name of the field (default: created_at)

        Returns:
            The model field attribute

        Raises:
            AttributeError: If the field does not exist
        """
        if field_name is None:
            field_name = "created_at"

        if not hasattr(self._model, field_name):
            raise AttributeError(
                f"Model {self._model.__name__} does not have field '{field_name}'"
            )

        return getattr(self._model, field_name)

    @property
    def model(self) -> type[ModelType]:
        """Get the model class this repository manages."""
        return self._model

    @property
    def session(self) -> AsyncSession:
        """Get the database session."""
        return self._session


__all__ = [
    "SQLAlchemyRepositoryBase",
    "ModelType",
]
