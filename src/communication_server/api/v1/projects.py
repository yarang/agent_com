"""
Project API endpoints for multi-tenancy support.

Provides CRUD operations for projects with owner-centered permissions.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_comm_core.db.models.project import ProjectDB, ProjectStatus
from agent_comm_core.models.auth import User
from communication_server.security.authorization import Permission, require_permission

router = APIRouter(prefix="/projects", tags=["Projects"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ProjectCreate(BaseModel):
    """Request model for creating a project."""

    project_id: str = Field(..., description="Human-readable project ID", min_length=1)
    name: str = Field(..., description="Project name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Project description", max_length=2000)
    allow_cross_project: bool = Field(default=False, description="Allow cross-project access")


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""

    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    status: str | None = Field(None)
    allow_cross_project: bool | None = Field(None)


class ProjectResponse(BaseModel):
    """Response model for project."""

    id: UUID = Field(..., description="Project UUID")
    project_id: str = Field(..., description="Human-readable project ID")
    owner_id: UUID = Field(..., description="Owner UUID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Project description")
    status: str = Field(..., description="Project status")
    allow_cross_project: bool = Field(..., description="Allow cross-project access")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class AgentInvite(BaseModel):
    """Request model for inviting an agent to a project."""

    agent_id: UUID = Field(..., description="Agent UUID to invite")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """
    Create a new project.

    Requires PROJECT_CREATE permission. The current user becomes the owner.

    Args:
        project_data: Project creation data
        current_user: Current authenticated user

    Returns:
        Created project
    """
    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Check if project_id already exists
        from sqlalchemy import select

        existing = await session.execute(
            select(ProjectDB).where(ProjectDB.project_id == project_data.project_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with ID '{project_data.project_id}' already exists",
            )

        # Create project
        project = ProjectDB(
            owner_id=current_user.id,
            project_id=project_data.project_id,
            name=project_data.name,
            description=project_data.description,
            allow_cross_project=project_data.allow_cross_project,
            status=ProjectStatus.ACTIVE,
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Log audit
        from agent_comm_core.db.models.audit_log import (
            ActorType,
            AuditAction,
            EntityType,
        )
        from agent_comm_core.services.audit_log import get_audit_log_service

        audit_service = get_audit_log_service(session)
        await audit_service.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.PROJECT,
            entity_id=project.id,
            project_id=project.id,
            actor_type=ActorType.USER,
            actor_id=current_user.id,
            action_details={"name": project.name, "project_id": project.project_id},
        )

        return ProjectResponse(
            id=project.id,
            project_id=project.project_id,
            owner_id=project.owner_id,
            name=project.name,
            description=project.description,
            status=project.status.value,
            allow_cross_project=project.allow_cross_project,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List projects accessible to the current user.

    Requires PROJECT_READ permission.

    Args:
        current_user: Current authenticated user
        skip: Number of projects to skip
        limit: Maximum number of projects to return

    Returns:
        List of projects
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Build query
        stmt = select(ProjectDB)

        # Non-superusers only see their own projects
        if not current_user.is_superuser:
            stmt = stmt.where(ProjectDB.owner_id == current_user.id)

        stmt = stmt.offset(skip).limit(limit)

        result = await session.execute(stmt)
        projects = result.scalars().all()

        return [
            ProjectResponse(
                id=p.id,
                project_id=p.project_id,
                owner_id=p.owner_id,
                name=p.name,
                description=p.description,
                status=p.status.value,
                allow_cross_project=p.allow_cross_project,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in projects
        ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id_str: str,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_READ))],
):
    """
    Get a project by ID.

    Requires PROJECT_READ permission.

    Args:
        project_id_str: Project ID (string)
        current_user: Current authenticated user

    Returns:
        Project details
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Try to parse as UUID first
        try:
            project_uuid = UUID(project_id_str)
            stmt = select(ProjectDB).where(ProjectDB.id == project_uuid)
        except ValueError:
            # Otherwise search by project_id string
            stmt = select(ProjectDB).where(ProjectDB.project_id == project_id_str)

        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Check permission
        if not current_user.is_superuser and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project",
            )

        return ProjectResponse(
            id=project.id,
            project_id=project.project_id,
            owner_id=project.owner_id,
            name=project.name,
            description=project.description,
            status=project.status.value,
            allow_cross_project=project.allow_cross_project,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id_str: str,
    project_data: ProjectUpdate,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """
    Update a project.

    Requires PROJECT_UPDATE permission and ownership.

    Args:
        project_id_str: Project ID (string)
        project_data: Update data
        current_user: Current authenticated user

    Returns:
        Updated project
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Find project
        try:
            project_uuid = UUID(project_id_str)
            stmt = select(ProjectDB).where(ProjectDB.id == project_uuid)
        except ValueError:
            stmt = select(ProjectDB).where(ProjectDB.project_id == project_id_str)

        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Check ownership
        if not current_user.is_superuser and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this project",
            )

        # Update fields
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.status is not None:
            project.status = project_data.status
        if project_data.allow_cross_project is not None:
            project.allow_cross_project = project_data.allow_cross_project

        await session.commit()
        await session.refresh(project)

        return ProjectResponse(
            id=project.id,
            project_id=project.project_id,
            owner_id=project.owner_id,
            name=project.name,
            description=project.description,
            status=project.status.value,
            allow_cross_project=project.allow_cross_project,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id_str: str,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECT_DELETE))],
):
    """
    Delete a project.

    Requires PROJECT_DELETE permission and ownership.

    Args:
        project_id_str: Project ID (string)
        current_user: Current authenticated user
    """
    from sqlalchemy import select

    from agent_comm_core.db.database import db_session

    async with db_session() as session:
        # Find project
        try:
            project_uuid = UUID(project_id_str)
            stmt = select(ProjectDB).where(ProjectDB.id == project_uuid)
        except ValueError:
            stmt = select(ProjectDB).where(ProjectDB.project_id == project_id_str)

        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Check ownership
        if not current_user.is_superuser and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this project",
            )

        await session.delete(project)
        await session.commit()
