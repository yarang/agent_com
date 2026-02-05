"""
Base classes for service layer.

This module provides reusable base service classes that eliminate code duplication
across all service implementations. It implements common business logic patterns
and provides consistent error handling across services.
"""

from typing import Any, Generic, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from agent_comm_core.models.common import DEFAULT_LIST_LIMIT, DEFAULT_LIST_OFFSET
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase

# Type variables for generic service
ServiceModelType = TypeVar("ServiceModelType", bound=DeclarativeBase)
RepositoryType = TypeVar("RepositoryType", bound=SQLAlchemyRepositoryBase)


class ServiceBase(Generic[ServiceModelType, RepositoryType]):
    """
    Generic base service for business logic.

    Provides common service operations that work with any repository.
    Reduces code duplication by providing common business logic patterns.

    Type Args:
        ServiceModelType: The model class this service manages
        RepositoryType: The repository class this service uses

    Example:
        class UserService(ServiceBase[UserDB, UserRepository]):
            def __init__(self, session: AsyncSession):
                repository = UserRepository(session, UserDB)
                super().__init__(repository)

            # Additional methods specific to User operations
            async def authenticate(self, username: str, password: str) -> UserDB | None:
                user = await self.get_by_username(username)
                if user and verify_password(password, user.password_hash):
                    return user
                return None
    """

    def __init__(self, repository: RepositoryType) -> None:
        """
        Initialize the service.

        Args:
            repository: The repository instance this service uses
        """
        self._repository = repository

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def get_by_id(self, id: Any) -> ServiceModelType | None:
        """
        Retrieve an entity by its ID.

        Args:
            id: Primary key value

        Returns:
            The entity if found, None otherwise
        """
        return await self._repository.get_by_id(id)

    async def get_by_id_or_404(self, id: Any) -> ServiceModelType:
        """
        Retrieve an entity by its ID or raise 404.

        Args:
            id: Primary key value

        Returns:
            The entity if found

        Raises:
            HTTPException: 404 if entity not found
        """
        entity = await self._repository.get_by_id(id)
        if entity is None:
            model_name = self._repository.model.__name__
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{model_name} with id {id} not found"
            )
        return entity

    async def get_by_ids(self, ids: list[Any]) -> list[ServiceModelType]:
        """
        Retrieve multiple entities by their IDs.

        Args:
            ids: List of primary key values

        Returns:
            List of entities (only those found)
        """
        return await self._repository.get_by_ids(ids)

    async def exists(self, id: Any) -> bool:
        """
        Check if an entity exists by its ID.

        Args:
            id: Primary key value

        Returns:
            True if entity exists, False otherwise
        """
        return await self._repository.exists(id)

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count entities with optional filters.

        Args:
            filters: Optional dictionary of field names to values for filtering

        Returns:
            Count of matching entities
        """
        return await self._repository.count(filters)

    async def list_all(
        self,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = DEFAULT_LIST_OFFSET,
        order_by: str | None = None,
        descending: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> list[ServiceModelType]:
        """
        List all entities with pagination and optional filtering.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            order_by: Field name to order by
            descending: Sort order (True = descending)
            filters: Optional dictionary of field names to values for filtering

        Returns:
            List of entities

        Raises:
            ValueError: If limit exceeds MAX_LIST_LIMIT
        """
        result = await self._repository.list_all(
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
            filters=filters,
        )
        return list(result.all())

    async def create(self, **kwargs: Any) -> ServiceModelType:
        """
        Create a new entity.

        Args:
            **kwargs: Field names and values for the new entity

        Returns:
            The created entity

        Raises:
            ValueError: If required fields are missing
        """
        return await self._repository.create(**kwargs)

    async def create_many(self, entities_data: list[dict[str, Any]]) -> list[ServiceModelType]:
        """
        Create multiple entities in a single operation.

        Args:
            entities_data: List of dictionaries containing entity data

        Returns:
            List of created entities
        """
        return await self._repository.create_many(entities_data)

    async def update(self, id: Any, **kwargs: Any) -> ServiceModelType | None:
        """
        Update an entity by its ID.

        Args:
            id: Primary key value
            **kwargs: Field names and values to update

        Returns:
            The updated entity if found, None otherwise
        """
        return await self._repository.update(id, **kwargs)

    async def update_or_404(self, id: Any, **kwargs: Any) -> ServiceModelType:
        """
        Update an entity by its ID or raise 404.

        Args:
            id: Primary key value
            **kwargs: Field names and values to update

        Returns:
            The updated entity

        Raises:
            HTTPException: 404 if entity not found
        """
        entity = await self._repository.update(id, **kwargs)
        if entity is None:
            model_name = self._repository.model.__name__
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{model_name} with id {id} not found"
            )
        return entity

    async def delete(self, id: Any) -> bool:
        """
        Delete an entity by its ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete(id)

    async def delete_or_404(self, id: Any) -> None:
        """
        Delete an entity by its ID or raise 404.

        Args:
            id: Primary key value

        Raises:
            HTTPException: 404 if entity not found
        """
        deleted = await self._repository.delete(id)
        if not deleted:
            model_name = self._repository.model.__name__
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{model_name} with id {id} not found"
            )

    async def soft_delete(self, id: Any) -> ServiceModelType | None:
        """
        Soft delete an entity by setting status to deleted.

        Args:
            id: Primary key value

        Returns:
            The updated entity if found, None otherwise
        """
        return await self._repository.soft_delete(id)

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    async def delete_many(self, ids: list[Any]) -> int:
        """
        Delete multiple entities by their IDs.

        Args:
            ids: List of primary key values

        Returns:
            Number of entities deleted
        """
        return await self._repository.delete_many(ids)

    async def update_many(self, ids: list[Any], **kwargs: Any) -> int:
        """
        Update multiple entities by their IDs.

        Args:
            ids: List of primary key values
            **kwargs: Field names and values to update

        Returns:
            Number of entities updated
        """
        return await self._repository.update_many(ids, **kwargs)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @property
    def repository(self) -> RepositoryType:
        """Get the repository instance."""
        return self._repository

    @property
    def model(self) -> type[ServiceModelType]:
        """Get the model class this service manages."""
        return self._repository.model  # type: ignore[return-value]


class SessionServiceBase(ServiceBase[ServiceModelType, RepositoryType]):
    """
    Base service that manages its own database session.

    This variant of ServiceBase creates its own repository instance
    from a database session, simplifying service initialization.

    Type Args:
        ServiceModelType: The model class this service manages
        RepositoryType: The repository class this service uses

    Example:
        class UserService(SessionServiceBase[UserDB, UserRepository]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, UserDB, UserRepository)
    """

    def __init__(
        self,
        session: AsyncSession,
        model: type[ServiceModelType],
        repository_class: type[RepositoryType],
    ) -> None:
        """
        Initialize the service with a database session.

        Args:
            session: SQLAlchemy async session
            model: The model class this service manages
            repository_class: The repository class to instantiate
        """
        repository = repository_class(session, model)
        super().__init__(repository)
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Get the database session."""
        return self._session


__all__ = [
    "ServiceBase",
    "SessionServiceBase",
    "ServiceModelType",
    "RepositoryType",
]
