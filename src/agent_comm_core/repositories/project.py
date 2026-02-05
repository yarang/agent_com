"""
Project repository for database operations.

Provides database access layer for ProjectDB model.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ScalarResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_comm_core.db.models.project import ProjectDB, ProjectStatus
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase


class ProjectRepository(SQLAlchemyRepositoryBase[ProjectDB]):
    """
    Repository for project database operations.

    Provides CRUD operations for ProjectDB entities.
    Extends the base repository with project specific operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, ProjectDB)

    # ========================================================================
    # Project Specific Operations
    # ========================================================================

    async def create(
        self,
        owner_id: UUID,
        project_id: str,
        name: str,
        description: str | None = None,
        status: str = ProjectStatus.ACTIVE,
        allow_cross_project: bool = False,
        settings: dict | None = None,
    ) -> ProjectDB:
        """
        Create a new project.

        Args:
            owner_id: User UUID who owns the project
            project_id: Human-readable unique project ID
            name: Project display name
            description: Optional project description
            status: Project status (default: ACTIVE)
            allow_cross_project: Whether cross-project access is allowed
            settings: Optional project settings as JSON

        Returns:
            Created project instance
        """
        project = await super().create(
            owner_id=owner_id,
            project_id=project_id,
            name=name,
            description=description,
            status=status,
            allow_cross_project=allow_cross_project,
            settings=settings,
        )
        await self._session.refresh(project)
        return project

    async def get_by_project_id(self, project_id: str) -> ProjectDB | None:
        """
        Get project by human-readable project ID.

        Args:
            project_id: Project identifier string

        Returns:
            Project instance or None
        """
        result = await self._session.execute(
            select(ProjectDB).where(ProjectDB.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project_id_with_owner(self, project_id: str) -> ProjectDB | None:
        """
        Get project by human-readable project ID with owner loaded.

        Args:
            project_id: Project identifier string

        Returns:
            Project instance with owner loaded or None
        """
        result = await self._session.execute(
            select(ProjectDB)
            .options(selectinload(ProjectDB.owner))
            .where(ProjectDB.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: UUID,
        limit: int = 100,
        offset: int = 0,
        include_archived: bool = False,
    ) -> ScalarResult[ProjectDB]:
        """
        List projects owned by a user.

        Args:
            owner_id: User UUID
            limit: Maximum number of results
            offset: Number of results to skip
            include_archived: Whether to include archived projects

        Returns:
            Scalar result of projects
        """
        query = select(ProjectDB).where(ProjectDB.owner_id == owner_id)

        if not include_archived:
            query = query.where(
                ProjectDB.status != ProjectStatus.ARCHIVED,
                ProjectDB.status != ProjectStatus.DELETED,
            )

        query = query.order_by(ProjectDB.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(query)
        return result.scalars()

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> ScalarResult[ProjectDB]:
        """
        List all projects with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status: Optional status filter

        Returns:
            Scalar result of projects
        """
        filters: dict[str, str] | None = None
        if status:
            filters = {"status": status}

        result = await super().list_all(
            limit=limit,
            offset=offset,
            order_by="created_at",
            descending=True,
            filters=filters,
        )

        # Exclude deleted projects by default if no status filter
        if status is None:
            # Need to re-query to exclude deleted properly
            query = select(ProjectDB).where(ProjectDB.status != ProjectStatus.DELETED)
            query = query.order_by(ProjectDB.created_at.desc()).limit(limit).offset(offset)
            result = await self._session.execute(query)
            return result.scalars()

        return result

    async def update(
        self,
        project_id: UUID,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        allow_cross_project: bool | None = None,
        settings: dict | None = None,
    ) -> ProjectDB | None:
        """
        Update a project.

        Args:
            project_id: Project UUID
            name: New name (optional)
            description: New description (optional)
            status: New status (optional)
            allow_cross_project: New cross-project setting (optional)
            settings: New settings (optional)

        Returns:
            Updated project instance or None
        """
        update_values: dict[str, str | bool | dict] = {}
        if name is not None:
            update_values["name"] = name
        if description is not None:
            update_values["description"] = description
        if status is not None:
            update_values["status"] = status
        if allow_cross_project is not None:
            update_values["allow_cross_project"] = allow_cross_project
        if settings is not None:
            update_values["settings"] = settings

        # Always update updated_at timestamp
        update_values["updated_at"] = datetime.now(UTC)

        return await super().update(project_id, **update_values)

    async def archive(self, project_id: UUID) -> ProjectDB | None:
        """
        Archive a project.

        Args:
            project_id: Project UUID

        Returns:
            Archived project instance or None
        """
        return await self.update(project_id, status=ProjectStatus.ARCHIVED)

    async def restore(self, project_id: UUID) -> ProjectDB | None:
        """
        Restore an archived project.

        Args:
            project_id: Project UUID

        Returns:
            Restored project instance or None
        """
        return await self.update(project_id, status=ProjectStatus.ACTIVE)

    async def delete(self, project_id: UUID, soft_delete: bool = True) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project UUID
            soft_delete: If True, mark as deleted; if False, actually delete

        Returns:
            True if deleted, False if not found
        """
        if soft_delete:
            result = await self._session.execute(
                update(ProjectDB)
                .where(ProjectDB.id == project_id)
                .values(status=ProjectStatus.DELETED)
            )
            return result.rowcount > 0
        else:
            result = await self._session.execute(
                delete(ProjectDB).where(ProjectDB.id == project_id)
            )
            return result.rowcount > 0

    async def project_id_exists(self, project_id: str) -> bool:
        """
        Check if a project ID exists.

        Args:
            project_id: Project identifier string

        Returns:
            True if project ID exists
        """
        result = await self._session.execute(
            select(ProjectDB.id).where(ProjectDB.project_id == project_id)
        )
        return result.scalar_one_or_none() is not None

    async def is_owner(self, project_id: UUID, user_id: UUID) -> bool:
        """
        Check if a user owns a project.

        Args:
            project_id: Project UUID
            user_id: User UUID

        Returns:
            True if user owns the project
        """
        result = await self._session.execute(
            select(ProjectDB.id).where(
                ProjectDB.id == project_id,
                ProjectDB.owner_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_owner_id(self, project_id: UUID) -> UUID | None:
        """
        Get the owner ID of a project.

        Args:
            project_id: Project UUID

        Returns:
            Owner UUID or None
        """
        result = await self._session.execute(
            select(ProjectDB.owner_id).where(ProjectDB.id == project_id)
        )
        return result.scalar_one_or_none()
