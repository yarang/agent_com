"""
Mappers for converting between ProjectRegistry models and database models.

This module provides mapper classes for converting between:
- ProjectDefinition (Pydantic) <-> ProjectDB (SQLAlchemy)
- ProjectAPIKey (Pydantic) <-> ProjectApiKeyDB (SQLAlchemy)
"""

import hashlib
from uuid import UUID

from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.project_api_key import ProjectApiKeyDB
from agent_comm_core.models.common import ProjectStatus
from mcp_broker.models.project import (
    ProjectAPIKey,
    ProjectConfig,
    ProjectDefinition,
    ProjectMetadata,
    ProjectStatistics,
)
from mcp_broker.models.project import (
    ProjectStatus as ProjectStatusModel,
)


class ApiKeyMapper:
    """
    Mapper for Project API keys between Pydantic and SQLAlchemy models.
    """

    @staticmethod
    def to_db_key_hash(api_key: str) -> tuple[str, str]:
        """
        Generate SHA-256 hash and prefix from an API key.

        Args:
            api_key: The full API key string

        Returns:
            Tuple of (api_key_hash, key_prefix)
        """
        # Generate SHA-256 hash
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Extract prefix (first 20 characters for identification)
        key_prefix = api_key[:20]

        return api_key_hash, key_prefix

    @staticmethod
    def to_db(
        project_api_key: ProjectAPIKey,
        project_uuid: UUID,
        created_by_id: UUID | None = None,
    ) -> ProjectApiKeyDB:
        """
        Convert ProjectAPIKey (Pydantic) to ProjectApiKeyDB (SQLAlchemy).

        Args:
            project_api_key: Pydantic model
            project_uuid: Project UUID (foreign key)
            created_by_id: User UUID who created the key

        Returns:
            ProjectApiKeyDB instance
        """
        api_key_hash, key_prefix = ApiKeyMapper.to_db_key_hash(project_api_key.api_key)

        return ProjectApiKeyDB(
            project_uuid=project_uuid,
            key_id=project_api_key.key_id,
            api_key_hash=api_key_hash,
            key_prefix=key_prefix,
            is_active=project_api_key.is_active,
            expires_at=project_api_key.expires_at,
            created_by_id=created_by_id,
            created_at=project_api_key.created_at,
        )

    @staticmethod
    def from_db(
        db_key: ProjectApiKeyDB,
        api_key_secret: str | None = None,
    ) -> ProjectAPIKey:
        """
        Convert ProjectApiKeyDB (SQLAlchemy) to ProjectAPIKey (Pydantic).

        Note: The api_key field requires the secret. If not provided,
        a placeholder is used (the full key is never stored in DB).

        Args:
            db_key: SQLAlchemy model
            api_key_secret: Optional API key secret for reconstruction

        Returns:
            ProjectAPIKey instance
        """
        # Reconstruct API key if secret provided, otherwise use hash placeholder
        if api_key_secret:
            api_key = api_key_secret  # Caller must provide the full key
        else:
            # For loading from DB, we can't reconstruct the full key
            # The registry will need to handle this case
            api_key = f"REDACTED_{db_key.key_prefix}"

        return ProjectAPIKey(
            key_id=db_key.key_id,
            api_key=api_key,
            created_at=db_key.created_at,
            expires_at=db_key.expires_at,
            is_active=db_key.is_active,
        )


class ProjectMapper:
    """
    Mapper for Projects between Pydantic and SQLAlchemy models.
    """

    @staticmethod
    def to_db(
        project: ProjectDefinition,
        owner_uuid: UUID,
    ) -> dict:
        """
        Convert ProjectDefinition (Pydantic) to ProjectDB fields.

        Args:
            project: Pydantic model
            owner_uuid: Owner UUID (foreign key)

        Returns:
            Dictionary of fields for ProjectDB creation
        """
        return {
            "owner_id": owner_uuid,
            "project_id": project.project_id,
            "name": project.metadata.name,
            "description": project.metadata.description,
            "status": project.status.status or ProjectStatus.ACTIVE,
            "allow_cross_project": project.config.allow_cross_project,
            "settings": {
                "tags": project.metadata.tags,
                "discoverable": project.config.discoverable,
                "shared_protocols": project.config.shared_protocols,
                **project.config.model_dump(exclude={"tags", "discoverable", "shared_protocols"}),
            },
        }

    @staticmethod
    def from_db(
        db_project: ProjectDB,
        api_keys_db: list[ProjectApiKeyDB] | None = None,
    ) -> ProjectDefinition:
        """
        Convert ProjectDB (SQLAlchemy) to ProjectDefinition (Pydantic).

        Args:
            db_project: SQLAlchemy model
            api_keys_db: Optional list of API keys from database

        Returns:
            ProjectDefinition instance

        Note:
            API keys returned from DB will have placeholder api_key values.
            The registry needs to handle this by either generating new keys
            or using a secure storage mechanism for active keys.
        """
        # Extract settings
        settings = db_project.settings or {}
        tags = settings.get("tags", [])
        discoverable = settings.get("discoverable", True)
        shared_protocols = settings.get("shared_protocols", [])

        # Convert API keys if provided
        api_keys = []
        if api_keys_db:
            for db_key in api_keys_db:
                # Note: API keys from DB don't have the secret
                # The registry will need to handle this
                api_keys.append(
                    ProjectAPIKey(
                        key_id=db_key.key_id,
                        api_key=f"REDACTED_{db_key.key_prefix}",  # Placeholder
                        created_at=db_key.created_at,
                        expires_at=db_key.expires_at,
                        is_active=db_key.is_active,
                    )
                )

        # Create metadata
        metadata = ProjectMetadata(
            name=db_project.name,
            description=db_project.description or "",
            tags=tags,
            owner=None,  # Owner info not directly in ProjectDB
        )

        # Create config
        config = ProjectConfig(
            max_sessions=settings.get("max_sessions", 100),
            max_protocols=settings.get("max_protocols", 50),
            max_message_queue_size=settings.get("max_message_queue_size", 100),
            allow_cross_project=db_project.allow_cross_project,
            discoverable=discoverable,
            shared_protocols=shared_protocols,
        )

        # Create status
        status = ProjectStatusModel(
            status=db_project.status or "active",
            created_at=db_project.created_at,
            last_modified=db_project.updated_at,
        )

        # Create statistics (not persisted in DB, use defaults)
        statistics = ProjectStatistics()

        return ProjectDefinition(
            project_id=db_project.project_id,
            metadata=metadata,
            api_keys=api_keys,
            config=config,
            cross_project_permissions=[],  # Not persisted in current schema
            statistics=statistics,
            status=status,
        )


__all__ = ["ApiKeyMapper", "ProjectMapper"]
