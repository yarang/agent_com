"""
Project registry for managing multi-project isolation with database persistence.

This module provides the ProjectRegistry class which manages
project definitions, API keys, and project-scoped storage with
write-through caching to the database.
"""

import hashlib
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID

from agent_comm_core.db.database import db_session
from mcp_broker.core.logging import get_logger
from mcp_broker.models.project import (
    ProjectAPIKey,
    ProjectConfig,
    ProjectDefinition,
    ProjectInfo,
    ProjectMetadata,
)
from mcp_broker.project.mappers import ApiKeyMapper, ProjectMapper

logger = get_logger(__name__)


# Type alias for session factory
SessionFactory = AsyncGenerator[object]


class ProjectRegistry:
    """
    Registry for managing projects and their configurations.

    The ProjectRegistry maintains all project definitions, handles
    API key generation and validation, and provides project-scoped
    storage namespace management.

    Uses a hybrid approach with in-memory cache and database persistence:
    - In-memory cache for fast access
    - Write-through cache: all writes update both cache and DB
    - Projects are loaded from DB on startup

    Attributes:
        _projects: Dict mapping project_id to ProjectDefinition
        _db_session_factory: Async session factory for database operations
        _api_key_secrets: Dict mapping (project_id, key_id) to api_key_secret
                          (Secrets are never stored in DB, only in memory)
    """

    def __init__(self, db_session_factory: SessionFactory | None = None) -> None:
        """
        Initialize the project registry.

        Args:
            db_session_factory: Optional async session factory for DB operations.
                              If None, registry operates in memory-only mode.
        """
        self._projects: dict[str, ProjectDefinition] = {}
        self._db_session_factory = db_session_factory
        self._api_key_secrets: dict[tuple[str, str], str] = {}

        logger.info(
            "ProjectRegistry initialized",
            extra={"context": {"database_enabled": db_session_factory is not None}},
        )

    def _generate_api_key(
        self,
        project_id: str,
        key_id: str,
        secret_length: int = 32,
    ) -> str:
        """
        Generate a new API key.

        Args:
            project_id: Project identifier
            key_id: Key identifier (e.g., 'default', 'admin')
            secret_length: Length of random secret

        Returns:
            Generated API key
        """
        secret = secrets.token_urlsafe(secret_length)[:secret_length]
        return f"{project_id}_{key_id}_{secret}"

    def _generate_key_id(self) -> str:
        """
        Generate a unique key identifier.

        Returns:
            Unique key ID
        """
        return f"key_{secrets.token_hex(4)}"

    async def load_from_database(self) -> int:
        """
        Load all projects from the database into the in-memory cache.

        Returns:
            Number of projects loaded

        Note:
            API key secrets are not stored in the database, so loaded
            projects will have placeholder API keys. New keys will need
            to be generated or existing secrets must be re-imported.
        """
        if not self._db_session_factory:
            logger.warning("Database session factory not configured, skipping database load")
            return 0

        loaded_count = 0

        try:
            async with db_session() as session:
                from agent_comm_core.repositories import ProjectApiKeyRepository, ProjectRepository

                project_repo = ProjectRepository(session)
                key_repo = ProjectApiKeyRepository(session)

                # Get all projects from database
                projects_result = await project_repo.list_all(
                    limit=1000,
                    include_archived=False,
                )

                async for db_project in projects_result:
                    # Load API keys for this project
                    api_keys_db = await key_repo.get_by_project_uuid(db_project.id)

                    # Convert to ProjectDefinition
                    project = ProjectMapper.from_db(db_project, api_keys_db)

                    # Store in cache
                    self._projects[project.project_id] = project
                    loaded_count += 1

                    logger.debug(
                        f"Loaded project from database: {project.project_id}",
                        extra={"context": {"project_id": project.project_id}},
                    )

                logger.info(
                    f"Loaded {loaded_count} projects from database",
                    extra={"context": {"count": loaded_count}},
                )

        except Exception as e:
            logger.error(
                f"Failed to load projects from database: {e}",
                extra={"context": {"error": str(e)}},
            )
            # Continue with in-memory projects only

        return loaded_count

    async def _save_to_database(
        self,
        project: ProjectDefinition,
        owner_uuid: UUID,
    ) -> bool:
        """
        Save a project to the database.

        Args:
            project: Project definition to save
            owner_uuid: UUID of the project owner

        Returns:
            True if saved successfully, False otherwise
        """
        if not self._db_session_factory:
            return False

        try:
            async with db_session() as session:
                from agent_comm_core.repositories import ProjectApiKeyRepository, ProjectRepository

                project_repo = ProjectRepository(session)
                key_repo = ProjectApiKeyRepository(session)

                # Check if project already exists in DB
                existing_db = await project_repo.get_by_project_id(project.project_id)

                if existing_db:
                    # Update existing project
                    db_fields = ProjectMapper.to_db(project, owner_uuid)
                    await project_repo.update(
                        existing_db.id,
                        **{k: v for k, v in db_fields.items() if k != "project_id"},
                    )
                    project_uuid = existing_db.id
                else:
                    # Create new project in DB
                    db_fields = ProjectMapper.to_db(project, owner_uuid)
                    new_db_project = await project_repo.create(**db_fields)
                    project_uuid = new_db_project.id

                # Save API keys
                for api_key in project.api_keys:
                    # Check if key already exists
                    existing_key = await key_repo.get_by_key_id(api_key.key_id)

                    # Store the secret in memory for validation
                    self._api_key_secrets[(project.project_id, api_key.key_id)] = api_key.api_key

                    if not existing_key:
                        # Only create new keys (don't update existing ones to preserve secrets)
                        api_key_hash, key_prefix = ApiKeyMapper.to_db_key_hash(api_key.api_key)
                        await key_repo.create(
                            project_uuid=project_uuid,
                            key_id=api_key.key_id,
                            api_key_hash=api_key_hash,
                            key_prefix=key_prefix,
                            created_by_id=owner_uuid,
                        )

                logger.debug(
                    f"Saved project to database: {project.project_id}",
                    extra={"context": {"project_id": project.project_id}},
                )

                return True

        except Exception as e:
            logger.error(
                f"Failed to save project to database: {e}",
                extra={"context": {"error": str(e), "project_id": project.project_id}},
            )
            return False

    async def _delete_from_database(self, project_id: str) -> bool:
        """
        Delete a project from the database.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._db_session_factory:
            return False

        try:
            async with db_session() as session:
                from agent_comm_core.repositories import ProjectApiKeyRepository, ProjectRepository

                project_repo = ProjectRepository(session)
                key_repo = ProjectApiKeyRepository(session)

                # Get the project DB record
                db_project = await project_repo.get_by_project_id(project_id)
                if not db_project:
                    return False

                # Delete all API keys first
                await key_repo.delete_by_project(db_project.id)

                # Delete the project
                await project_repo.delete(db_project.id)

                logger.debug(
                    f"Deleted project from database: {project_id}",
                    extra={"context": {"project_id": project_id}},
                )

                return True

        except Exception as e:
            logger.error(
                f"Failed to delete project from database: {e}",
                extra={"context": {"error": str(e), "project_id": project_id}},
            )
            return False

    async def create_project(
        self,
        project_id: str,
        name: str,
        description: str = "",
        config: ProjectConfig | None = None,
        tags: list[str] | None = None,
        owner: str | None = None,
        owner_uuid: UUID | None = None,
    ) -> ProjectDefinition:
        """
        Create a new project with generated API keys.

        Args:
            project_id: Unique project identifier
            name: Human-readable project name
            description: Optional project description
            config: Optional project configuration
            tags: Optional searchable tags
            owner: Optional owner identifier (string, for backward compatibility)
            owner_uuid: Optional owner UUID (required for database persistence)

        Returns:
            Created project definition

        Raises:
            ValueError: If project already exists or validation fails
        """
        if project_id in self._projects:
            logger.warning(
                f"Project {project_id} already exists",
                extra={"context": {"project_id": project_id}},
            )
            raise ValueError(f"Project '{project_id}' already exists")

        # Create metadata
        metadata = ProjectMetadata(
            name=name,
            description=description,
            tags=tags or [],
            owner=owner,
        )

        # Use provided config or default
        project_config = config or ProjectConfig()

        # Generate initial API key
        key_id = self._generate_key_id()
        api_key = self._generate_api_key(project_id, key_id)

        project_api_key = ProjectAPIKey(
            key_id=key_id,
            api_key=api_key,
            is_active=True,
        )

        # Create project definition
        project = ProjectDefinition(
            project_id=project_id,
            metadata=metadata,
            api_keys=[project_api_key],
            config=project_config,
        )

        # Store in cache
        self._projects[project_id] = project

        # Store API key secret in memory
        self._api_key_secrets[(project_id, key_id)] = api_key

        # Save to database if session factory available
        if owner_uuid and self._db_session_factory:
            await self._save_to_database(project, owner_uuid)

        logger.info(
            f"Created project: {project_id}",
            extra={
                "context": {
                    "project_id": project_id,
                    "name": name,
                    "config": project_config.model_dump(),
                }
            },
        )

        return project

    async def get_project(self, project_id: str) -> ProjectDefinition | None:
        """
        Get a project by ID.

        Args:
            project_id: Project identifier

        Returns:
            ProjectDefinition if found, None otherwise
        """
        return self._projects.get(project_id)

    async def list_projects(
        self,
        name_filter: str | None = None,
        include_inactive: bool = False,
        _include_stats: bool = False,
    ) -> list[ProjectInfo]:
        """
        List projects with optional filtering.

        Args:
            name_filter: Optional partial name match filter
            include_inactive: Whether to include inactive projects
            _include_stats: Whether to include full statistics (reserved for future use)

        Returns:
            List of project information (public view)
        """
        projects = list(self._projects.values())

        # Filter by status
        if not include_inactive:
            projects = [p for p in projects if p.is_active()]

        # Filter by name
        if name_filter:
            projects = [p for p in projects if name_filter.lower() in p.metadata.name.lower()]

        # Convert to public info
        result = [
            ProjectInfo.from_definition(p)
            for p in projects
            if p.metadata.discoverable or p.config.discoverable
        ]

        logger.debug(
            f"Listed {len(result)} projects",
            extra={"context": {"name_filter": name_filter, "include_inactive": include_inactive}},
        )

        return result

    async def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        config: ProjectConfig | None = None,
        tags: list[str] | None = None,
    ) -> ProjectDefinition:
        """
        Update an existing project.

        Args:
            project_id: Project identifier
            name: New name (optional)
            description: New description (optional)
            config: New configuration (optional)
            tags: New tags (optional)

        Returns:
            Updated project definition

        Raises:
            ValueError: If project not found
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        # Update metadata
        if name is not None:
            project.metadata.name = name
        if description is not None:
            project.metadata.description = description
        if tags is not None:
            project.metadata.tags = tags

        # Update config
        if config is not None:
            project.config = config

        # Update last modified
        from copy import deepcopy

        old_status = project.status
        project.status = deepcopy(old_status)
        project.status.last_modified = datetime.now(UTC)

        # Sync to database if available
        if self._db_session_factory:
            # Get the owner UUID from the database project
            try:
                async with db_session() as session:
                    from agent_comm_core.repositories import ProjectRepository

                    project_repo = ProjectRepository(session)
                    db_project = await project_repo.get_by_project_id(project_id)
                    if db_project:
                        await self._save_to_database(project, db_project.owner_id)
            except Exception as e:
                logger.warning(
                    f"Failed to sync project update to database: {e}",
                    extra={"context": {"error": str(e), "project_id": project_id}},
                )

        logger.info(
            f"Updated project: {project_id}",
            extra={"context": {"project_id": project_id}},
        )

        return project

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If project has active sessions or pending messages
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        # Check if project can be deleted
        if project.statistics.session_count > 0:
            raise ValueError(f"Cannot delete project '{project_id}' with active sessions")

        # Delete from database first
        if self._db_session_factory:
            await self._delete_from_database(project_id)

        # Delete from cache
        del self._projects[project_id]

        # Clean up API key secrets
        keys_to_remove = [
            (pid, kid) for (pid, kid) in self._api_key_secrets if pid == project_id
        ]
        for key in keys_to_remove:
            del self._api_key_secrets[key]

        logger.info(
            f"Deleted project: {project_id}",
            extra={"context": {"project_id": project_id}},
        )

        return True

    async def validate_api_key(
        self,
        api_key: str,
    ) -> tuple[str, str] | None:
        """
        Validate an API key and extract project and key IDs.

        Args:
            api_key: API key string to validate

        Returns:
            Tuple of (project_id, key_id) if valid, None otherwise
        """
        try:
            # Split from right to handle project_ids with underscores
            parts = api_key.rsplit("_", 2)
            if len(parts) != 3:
                return None

            project_id, key_id, _secret = parts

            # Check if project exists
            project = await self.get_project(project_id)
            if not project:
                return None

            # Check against stored secrets first (for keys generated by this registry)
            stored_secret = self._api_key_secrets.get((project_id, key_id))
            if stored_secret and stored_secret == api_key:
                # Verify key is still active and not expired
                for project_key in project.api_keys:
                    if project_key.key_id == key_id:
                        if not project_key.is_active:
                            return None
                        if project_key.expires_at:
                            now = datetime.now(UTC)
                            if project_key.expires_at < now:
                                return None
                        break

                logger.debug(
                    f"API key validated for project: {project_id}",
                    extra={"context": {"project_id": project_id, "key_id": key_id}},
                )
                return (project_id, key_id)

            # If not in memory secrets, validate against database hash
            if self._db_session_factory:
                try:
                    async with db_session() as session:
                        from agent_comm_core.repositories import ProjectApiKeyRepository

                        key_repo = ProjectApiKeyRepository(session)

                        # Compute hash of provided key
                        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

                        # Look up by hash
                        db_key = await key_repo.get_by_hash(api_key_hash)
                        if db_key and db_key.is_valid:
                            logger.debug(
                                f"API key validated for project: {project_id}",
                                extra={"context": {"project_id": project_id, "key_id": key_id}},
                            )
                            return (project_id, key_id)
                except Exception as e:
                    logger.warning(
                        f"Database API key validation failed: {e}",
                        extra={"context": {"error": str(e)}},
                    )

            return None

        except Exception:
            return None

    async def rotate_api_keys(
        self,
        project_id: str,
        key_id: str | None = None,
        grace_period_seconds: int = 300,
    ) -> list[ProjectAPIKey]:
        """
        Rotate API keys for a project.

        Args:
            project_id: Project identifier
            key_id: Specific key to rotate (None = all keys)
            grace_period_seconds: Grace period before old keys expire

        Returns:
            List of new API keys

        Raises:
            ValueError: If project not found
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        now = datetime.now(UTC)
        expiration = now + timedelta(seconds=grace_period_seconds)
        new_keys: list[ProjectAPIKey] = []

        if key_id:
            # Rotate specific key
            for project_key in project.api_keys:
                if project_key.key_id == key_id:
                    # Set expiration on old key
                    project_key.expires_at = expiration

                    # Generate new key
                    new_key_id = self._generate_key_id()
                    new_api_key = self._generate_api_key(project_id, new_key_id)

                    new_project_key = ProjectAPIKey(
                        key_id=new_key_id,
                        api_key=new_api_key,
                        is_active=True,
                    )
                    new_keys.append(new_project_key)
                    project.api_keys.append(new_project_key)

                    # Store secret in memory
                    self._api_key_secrets[(project_id, new_key_id)] = new_api_key

                    logger.info(
                        f"Rotated API key {key_id} for project: {project_id}",
                        extra={"context": {"project_id": project_id, "key_id": key_id}},
                    )
                    break
        else:
            # Rotate all keys
            for project_key in project.api_keys:
                # Set expiration on old key
                project_key.expires_at = expiration

                # Generate new key
                new_key_id = self._generate_key_id()
                new_api_key = self._generate_api_key(project_id, new_key_id)

                new_project_key = ProjectAPIKey(
                    key_id=new_key_id,
                    api_key=new_api_key,
                    is_active=True,
                )
                new_keys.append(new_project_key)
                project.api_keys.append(new_project_key)

                # Store secret in memory
                self._api_key_secrets[(project_id, new_key_id)] = new_api_key

            logger.info(
                f"Rotated all API keys for project: {project_id}",
                extra={"context": {"project_id": project_id}},
            )

        # Sync to database if available
        if self._db_session_factory:
            try:
                async with db_session() as session:
                    from agent_comm_core.repositories import ProjectRepository

                    project_repo = ProjectRepository(session)
                    db_project = await project_repo.get_by_project_id(project_id)
                    if db_project:
                        await self._save_to_database(project, db_project.owner_id)
            except Exception as e:
                logger.warning(
                    f"Failed to sync API key rotation to database: {e}",
                    extra={"context": {"error": str(e), "project_id": project_id}},
                )

        return new_keys

    async def update_statistics(
        self,
        project_id: str,
        session_count_delta: int = 0,
        message_count_delta: int = 0,
        protocol_count_delta: int = 0,
    ) -> None:
        """
        Update project statistics.

        Args:
            project_id: Project identifier
            session_count_delta: Change in session count
            message_count_delta: Change in message count
            protocol_count_delta: Change in protocol count
        """
        project = self._projects.get(project_id)
        if not project:
            return

        project.statistics.session_count += session_count_delta
        project.statistics.message_count += message_count_delta
        project.statistics.protocol_count += protocol_count_delta
        project.statistics.last_activity = datetime.now(UTC)

    def _ensure_default_project(self) -> None:
        """Ensure the default project exists for backward compatibility."""
        if "default" not in self._projects:
            default_project = ProjectDefinition(
                project_id="default",
                metadata=ProjectMetadata(
                    name="Default Project",
                    description="Default project for backward compatibility",
                ),
                api_keys=[
                    ProjectAPIKey(
                        key_id="default",
                        api_key="default_default_abcdefghijklmnopqrstuvwxyz123456",
                        is_active=True,
                    )
                ],
            )
            self._projects["default"] = default_project

            # Store secret in memory
            self._api_key_secrets[("default", "default")] = (
                "default_default_abcdefghijklmnopqrstuvwxyz123456"
            )

            logger.info("Created default project for backward compatibility")


# =============================================================================
# Global Project Registry Singleton
# =============================================================================

_global_registry: ProjectRegistry | None = None


def get_project_registry(
    db_session_factory: SessionFactory | None = None,
) -> ProjectRegistry:
    """
    Get the global project registry instance.

    Args:
        db_session_factory: Optional async session factory for DB operations.

    Returns:
        The global ProjectRegistry instance

    Example:
        >>> registry = get_project_registry()
        >>> project = await registry.get_project("my_project")

    Note:
        If db_session_factory is provided on first call, it will be used
        for all subsequent database operations. The factory should be an
        async generator that yields database sessions.
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = ProjectRegistry(db_session_factory)

    return _global_registry


def reset_project_registry() -> None:
    """
    Reset the global project registry.

    This is primarily useful for testing purposes.

    Warning:
        This will clear all project data from the registry.
    """
    global _global_registry

    _global_registry = None
    logger.debug("Project registry reset")
