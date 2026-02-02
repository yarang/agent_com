"""
Audit logging service for security event tracking.

Provides centralized audit logging for all critical security actions.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.audit_log import (
    ActorType,
    AuditAction,
    AuditLogDB,
    EntityType,
)
from agent_comm_core.models.audit_log import (
    AuditLogCreate,
    AuditLogFilter,
    AuditLogResponse,
)
from agent_comm_core.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLogDB, AuditLogCreate]):
    """Repository for audit log operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: int) -> AuditLogDB | None:
        """Retrieve an audit log by its ID.

        Args:
            id: Audit log ID

        Returns:
            The audit log if found, None otherwise
        """
        result = await self._session.execute(select(AuditLogDB).where(AuditLogDB.id == id))
        return result.scalar_one_or_none()

    async def create(self, data: AuditLogCreate) -> AuditLogDB:
        """Create a new audit log entry.

        Args:
            data: Audit log creation data

        Returns:
            The created audit log
        """
        audit_log = AuditLogDB(
            action=data.action,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            project_id=data.project_id,
            actor_type=data.actor_type,
            actor_id=data.actor_id,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
            action_details=data.action_details,
            status=data.status,
            occurred_at=data.occurred_at or datetime.now(UTC),
        )
        self._session.add(audit_log)
        await self._session.flush()
        return audit_log

    async def update(self, id: int, data: dict[str, Any]) -> AuditLogDB | None:
        """Update an audit log entry.

        NOTE: Audit logs should be immutable. This method exists only for
        special cases like status updates on failed async operations.

        Args:
            id: Audit log ID
            data: Fields to update

        Returns:
            The updated audit log if found, None otherwise
        """
        audit_log = await self.get_by_id(id)
        if not audit_log:
            return None

        for key, value in data.items():
            if hasattr(audit_log, key):
                setattr(audit_log, key, value)

        await self._session.flush()
        return audit_log

    async def delete(self, id: int) -> bool:
        """Delete an audit log entry.

        NOTE: Audit logs should never be deleted. This method exists
        only for GDPR compliance requests.

        Args:
            id: Audit log ID

        Returns:
            True if deleted, False if not found
        """
        audit_log = await self.get_by_id(id)
        if not audit_log:
            return False

        await self._session.delete(audit_log)
        await self._session.flush()
        return True

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[AuditLogDB]:
        """List all audit logs with pagination.

        Args:
            limit: Maximum number of audit logs to return
            offset: Number of audit logs to skip

        Returns:
            List of audit logs
        """
        result = await self._session.execute(
            select(AuditLogDB).order_by(AuditLogDB.occurred_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def query(self, filters: AuditLogFilter) -> list[AuditLogDB]:
        """Query audit logs with filters.

        Args:
            filters: Query filters

        Returns:
            List of matching audit logs
        """
        stmt = select(AuditLogDB).order_by(AuditLogDB.occurred_at.desc())

        if filters.action:
            stmt = stmt.where(AuditLogDB.action == filters.action)
        if filters.entity_type:
            stmt = stmt.where(AuditLogDB.entity_type == filters.entity_type)
        if filters.entity_id:
            stmt = stmt.where(AuditLogDB.entity_id == filters.entity_id)
        if filters.project_id:
            stmt = stmt.where(AuditLogDB.project_id == filters.project_id)
        if filters.actor_type:
            stmt = stmt.where(AuditLogDB.actor_type == filters.actor_type)
        if filters.actor_id:
            stmt = stmt.where(AuditLogDB.actor_id == filters.actor_id)
        if filters.status:
            stmt = stmt.where(AuditLogDB.status == filters.status)
        if filters.start_date:
            stmt = stmt.where(AuditLogDB.occurred_at >= filters.start_date)
        if filters.end_date:
            stmt = stmt.where(AuditLogDB.occurred_at <= filters.end_date)

        if filters.limit:
            stmt = stmt.limit(filters.limit)
        if filters.offset:
            stmt = stmt.offset(filters.offset)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class AuditLogService:
    """Service for centralized audit logging."""

    def __init__(self, session: AsyncSession):
        """Initialize the audit log service.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._repository = AuditLogRepository(session)

    async def log(
        self,
        action: str | AuditAction,
        entity_type: str | EntityType,
        entity_id: UUID | None,
        actor_type: str | ActorType,
        actor_id: UUID | None,
        project_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        action_details: dict[str, Any] | None = None,
        status: str = "success",
        occurred_at: datetime | None = None,
    ) -> AuditLogDB:
        """Log an audit event.

        Args:
            action: The action performed
            entity_type: Type of entity affected
            entity_id: ID of entity affected
            actor_type: Type of actor (user/agent/system)
            actor_id: ID of actor
            project_id: Project context
            ip_address: Client IP address
            user_agent: Client user agent
            action_details: Additional details
            status: Status of action
            occurred_at: When the action occurred

        Returns:
            Created audit log entry
        """
        # Convert enums to strings
        if isinstance(action, AuditAction):
            action = action.value
        if isinstance(entity_type, EntityType):
            entity_type = entity_type.value
        if isinstance(actor_type, ActorType):
            actor_type = actor_type.value

        create_data = AuditLogCreate(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            actor_type=actor_type,
            actor_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action_details=action_details,
            status=status,
            occurred_at=occurred_at,
        )

        return await self._repository.create(create_data)

    async def log_from_request(
        self,
        request: Request,
        action: str | AuditAction,
        entity_type: str | EntityType,
        entity_id: UUID | None,
        actor_type: str | ActorType,
        actor_id: UUID | None,
        project_id: UUID | None = None,
        action_details: dict[str, Any] | None = None,
        status: str = "success",
    ) -> AuditLogDB:
        """Log an audit event from a FastAPI request.

        Args:
            request: FastAPI request object
            action: The action performed
            entity_type: Type of entity affected
            entity_id: ID of entity affected
            actor_type: Type of actor (user/agent/system)
            actor_id: ID of actor
            project_id: Project context
            action_details: Additional details
            status: Status of action

        Returns:
            Created audit log entry
        """
        # Extract IP and user agent from request
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        return await self.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            project_id=project_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action_details=action_details,
            status=status,
        )

    async def query(self, filters: AuditLogFilter) -> list[AuditLogResponse]:
        """Query audit logs.

        Args:
            filters: Query filters

        Returns:
            List of matching audit logs
        """
        logs = await self._repository.query(filters)
        return [
            AuditLogResponse(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                project_id=log.project_id,
                actor_type=log.actor_type,
                actor_id=log.actor_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                action_details=log.action_details,
                status=log.status,
                occurred_at=log.occurred_at,
            )
            for log in logs
        ]

    @asynccontextmanager
    async def audit_context(
        self,
        action: str | AuditAction,
        entity_type: str | EntityType,
        actor_type: str | ActorType,
        actor_id: UUID | None,
        project_id: UUID | None = None,
        entity_id: UUID | None = None,
    ):
        """Context manager for automatic audit logging.

        Logs the action on entry and logs any exceptions that occur.

        Usage:
            async with audit_service.audit_context(
                action=AuditAction.AUTH_LOGIN,
                entity_type=EntityType.USER,
                actor_type=ActorType.USER,
                actor_id=user_id,
            ) as audit:
                # Perform action
                result = await some_operation()
                audit.entity_id = result.id

        Args:
            action: The action being performed
            entity_type: Type of entity being affected
            actor_type: Type of actor
            actor_id: ID of actor
            project_id: Project context
            entity_id: ID of entity (can be set inside context)

        Yields:
            AuditLogCreate object that can be updated before logging
        """
        create_data = AuditLogCreate(
            action=action.value if isinstance(action, AuditAction) else action,
            entity_type=entity_type.value if isinstance(entity_type, EntityType) else entity_type,
            entity_id=entity_id,
            project_id=project_id,
            actor_type=actor_type.value if isinstance(actor_type, ActorType) else actor_type,
            actor_id=actor_id,
            status="success",
        )

        try:
            yield create_data
        except Exception:
            create_data.status = "error"
            create_data.action_details = create_data.action_details or {}
            create_data.action_details["error"] = str(
                create_data.action_details.get("error", "Unknown error")
            )
            raise
        finally:
            await self._repository.create(create_data)


def get_audit_log_service(session: AsyncSession) -> AuditLogService:
    """Get an audit log service instance.

    Args:
        session: SQLAlchemy async session

    Returns:
        AuditLogService instance
    """
    return AuditLogService(session)
