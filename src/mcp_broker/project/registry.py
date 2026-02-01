"""
Project registry for managing multi-project isolation.

This module provides the ProjectRegistry class which manages
project definitions, API keys, and project-scoped storage.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

from mcp_broker.core.logging import get_logger
from mcp_broker.models.project import (
    CrossProjectPermission,
    ProjectAPIKey,
    ProjectConfig,
    ProjectDefinition,
    ProjectInfo,
    ProjectMetadata,
    ProjectStatistics,
    ProjectStatus,
)

logger = get_logger(__name__)


class ProjectRegistry:
    """
    Registry for managing projects and their configurations.

    The ProjectRegistry maintains all project definitions, handles
    API key generation and validation, and provides project-scoped
    storage namespace management.

    Attributes:
        _projects: Dict mapping project_id to ProjectDefinition
    """

    def __init__(self) -> None:
        """Initialize the project registry."""
        self._projects: dict[str, ProjectDefinition] = {}

        logger.info("ProjectRegistry initialized")

    def _generate_api_key(
        self,
        project_id: str,
        key_id: str,
        secret_length: int = 32,
    ) -> str:
        """Generate a new API key.

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
        """Generate a unique key identifier.

        Returns:
            Unique key ID
        """
        return f"key_{secrets.token_hex(4)}"

    async def create_project(
        self,
        project_id: str,
        name: str,
        description: str = "",
        config: ProjectConfig | None = None,
        tags: list[str] | None = None,
        owner: str | None = None,
    ) -> ProjectDefinition:
        """Create a new project with generated API keys.

        Args:
            project_id: Unique project identifier
            name: Human-readable project name
            description: Optional project description
            config: Optional project configuration
            tags: Optional searchable tags
            owner: Optional owner identifier

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

        # Store project
        self._projects[project_id] = project

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
        """Get a project by ID.

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
        include_stats: bool = False,
    ) -> list[ProjectInfo]:
        """List projects with optional filtering.

        Args:
            name_filter: Optional partial name match filter
            include_inactive: Whether to include inactive projects
            include_stats: Whether to include full statistics

        Returns:
            List of project information (public view)
        """
        projects = list(self._projects.values())

        # Filter by status
        if not include_inactive:
            projects = [p for p in projects if p.is_active()]

        # Filter by name
        if name_filter:
            projects = [
                p for p in projects if name_filter.lower() in p.metadata.name.lower()
            ]

        # Convert to public info
        result = [
            ProjectInfo.from_definition(p) for p in projects if p.metadata.discoverable or p.config.discoverable
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
        """Update an existing project.

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

        logger.info(
            f"Updated project: {project_id}",
            extra={"context": {"project_id": project_id}},
        )

        return project

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project.

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
            raise ValueError(
                f"Cannot delete project '{project_id}' with active sessions"
            )

        # Delete project
        del self._projects[project_id]

        logger.info(
            f"Deleted project: {project_id}",
            extra={"context": {"project_id": project_id}},
        )

        return True

    async def validate_api_key(
        self,
        api_key: str,
    ) -> tuple[str, str] | None:
        """Validate an API key and extract project and key IDs.

        Args:
            api_key: API key string to validate

        Returns:
            Tuple of (project_id, key_id) if valid, None otherwise
        """
        try:
            parts = api_key.split("_", 2)
            if len(parts) != 3:
                return None

            project_id, key_id, _secret = parts

            # Check if project exists
            project = await self.get_project(project_id)
            if not project:
                return None

            # Check if key exists in project
            for project_key in project.api_keys:
                if project_key.key_id == key_id and project_key.api_key == api_key:
                    if not project_key.is_active:
                        return None

                    # Check expiration
                    if project_key.expires_at:
                        now = datetime.now(UTC)
                        if project_key.expires_at < now:
                            return None

                    logger.debug(
                        f"API key validated for project: {project_id}",
                        extra={"context": {"project_id": project_id, "key_id": key_id}},
                    )
                    return (project_id, key_id)

            return None

        except Exception:
            return None

    async def rotate_api_keys(
        self,
        project_id: str,
        key_id: str | None = None,
        grace_period_seconds: int = 300,
    ) -> list[ProjectAPIKey]:
        """Rotate API keys for a project.

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

            logger.info(
                f"Rotated all API keys for project: {project_id}",
                extra={"context": {"project_id": project_id}},
            )

        return new_keys

    async def update_statistics(
        self,
        project_id: str,
        session_count_delta: int = 0,
        message_count_delta: int = 0,
        protocol_count_delta: int = 0,
    ) -> None:
        """Update project statistics.

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
                        api_key="default_default_default",
                        is_active=True,
                    )
                ],
            )
            self._projects["default"] = default_project
            logger.info("Created default project for backward compatibility")
