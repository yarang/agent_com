"""
Protocol Registry for MCP Broker Server.

This module provides the ProtocolRegistry class responsible for
registering, validating, and discovering communication protocols.

Supports project-scoped protocol isolation with optional cross-project
protocol sharing (read-only references).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mcp_broker.core.logging import get_logger
from mcp_broker.models.protocol import (
    ProtocolDefinition,
    ProtocolInfo,
    ProtocolValidationError,
    ValidationResult,
)
from mcp_broker.storage.interface import StorageBackend

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


# Global protocol sharing registry for cross-project references
# Maps (source_project_id, protocol_name, protocol_version) -> set(target_project_ids)
_shared_protocols: dict[tuple[str, str, str], set[str]] = {}


class ProtocolRegistry:
    """
    Registry for managing communication protocols.

    The ProtocolRegistry handles:
    - Protocol registration with JSON Schema validation
    - Protocol discovery with filtering by name, version, tags
    - Duplicate prevention
    - Protocol metadata tracking

    Attributes:
        storage: Storage backend for protocol persistence
    """

    def __init__(self, storage: StorageBackend) -> None:
        """Initialize the protocol registry.

        Args:
            storage: Storage backend for persistence
        """
        self._storage = storage
        logger.info("ProtocolRegistry initialized")

    async def register(
        self, protocol: ProtocolDefinition, project_id: str = "default"
    ) -> ProtocolInfo:
        """Register a new protocol.

        Args:
            protocol: Protocol definition to register
            project_id: Project identifier for isolation (defaults to "default")

        Returns:
            ProtocolInfo with registration metadata

        Raises:
            ValueError: If protocol already exists or validation fails
        """
        # Check for duplicate within project
        existing = await self._storage.get_protocol(protocol.name, protocol.version, project_id)
        if existing:
            logger.warning(
                f"Protocol {protocol.name} v{protocol.version} already registered in project {project_id}",
                extra={
                    "context": {
                        "protocol_name": protocol.name,
                        "version": protocol.version,
                        "project_id": project_id,
                    }
                },
            )
            raise ValueError(
                f"Protocol '{protocol.name}' version '{protocol.version}' already exists in project '{project_id}'. "
                f"Please increment version or use a different name."
            )

        # Save to storage with project scope
        await self._storage.save_protocol(protocol, project_id)

        # Create protocol info
        info = ProtocolInfo(
            name=protocol.name,
            version=protocol.version,
            registered_at=datetime.now(UTC),
            capabilities=protocol.capabilities,
            metadata=protocol.metadata,
        )

        logger.info(
            f"Registered protocol: {protocol.name} v{protocol.version} in project {project_id}",
            extra={
                "context": {
                    "protocol_name": protocol.name,
                    "version": protocol.version,
                    "project_id": project_id,
                    "capabilities": protocol.capabilities,
                    "tags": protocol.metadata.tags if protocol.metadata else [],
                }
            },
        )

        return info

    async def discover(
        self,
        name: str | None = None,
        version: str | None = None,
        tags: list[str] | None = None,
        project_id: str = "default",
        include_shared: bool = False,
    ) -> list[ProtocolInfo]:
        """Discover protocols with optional filtering.

        Args:
            name: Filter by protocol name (optional)
            version: Filter by exact version or version range (optional)
            tags: Filter by capability tags (optional)
            project_id: Project identifier (defaults to "default")
            include_shared: Include protocols shared from other projects (optional)

        Returns:
            List of matching protocol info objects
        """
        protocols = await self._storage.list_protocols(
            name=name, version=version, project_id=project_id
        )

        # Convert to ProtocolInfo
        results = [
            ProtocolInfo(
                name=p.name,
                version=p.version,
                registered_at=datetime.now(UTC),  # In production, track actual registration time
                capabilities=p.capabilities,
                metadata=p.metadata,
            )
            for p in protocols
        ]

        # Add shared protocols if requested
        if include_shared:
            shared_protocols = await self._get_shared_protocols(project_id, name, version)
            for sp in shared_protocols:
                results.append(
                    ProtocolInfo(
                        name=sp.name,
                        version=sp.version,
                        registered_at=datetime.now(UTC),
                        capabilities=sp.capabilities,
                        metadata=sp.metadata,
                    )
                )

        # Filter by tags if specified
        if tags:
            results = [
                r for r in results if r.metadata and any(tag in r.metadata.tags for tag in tags)
            ]

        logger.debug(
            f"Protocol discovery: name={name}, version={version}, tags={tags}, project={project_id}, found={len(results)}",
            extra={
                "context": {
                    "filter_name": name,
                    "filter_version": version,
                    "filter_tags": tags,
                    "project_id": project_id,
                    "include_shared": include_shared,
                    "result_count": len(results),
                }
            },
        )

        return results

    async def share_protocol(
        self,
        name: str,
        version: str,
        source_project_id: str,
        target_project_id: str,
    ) -> bool:
        """Share a protocol with another project (read-only reference).

        Args:
            name: Protocol name
            version: Protocol version
            source_project_id: Source project that owns the protocol
            target_project_id: Target project to share with

        Returns:
            True if protocol was shared, False if not found

        Raises:
            ValueError: If trying to share with self or protocol doesn't exist
        """
        if source_project_id == target_project_id:
            raise ValueError("Cannot share protocol within the same project")

        # Check if protocol exists in source project
        protocol = await self._storage.get_protocol(name, version, source_project_id)
        if not protocol:
            return False

        # Add to shared registry
        key = (source_project_id, name, version)
        if key not in _shared_protocols:
            _shared_protocols[key] = set()

        _shared_protocols[key].add(target_project_id)

        logger.info(
            f"Shared protocol {name} v{version} from {source_project_id} to {target_project_id}",
            extra={
                "context": {
                    "protocol_name": name,
                    "version": version,
                    "source_project": source_project_id,
                    "target_project": target_project_id,
                }
            },
        )

        return True

    async def unshare_protocol(
        self,
        name: str,
        version: str,
        source_project_id: str,
        target_project_id: str,
    ) -> bool:
        """Remove protocol sharing with another project.

        Args:
            name: Protocol name
            version: Protocol version
            source_project_id: Source project that owns the protocol
            target_project_id: Target project to unshare from

        Returns:
            True if sharing was removed, False if not found
        """
        key = (source_project_id, name, version)
        if key not in _shared_protocols:
            return False

        if target_project_id not in _shared_protocols[key]:
            return False

        _shared_protocols[key].discard(target_project_id)

        # Clean up empty entries
        if not _shared_protocols[key]:
            del _shared_protocols[key]

        logger.info(
            f"Unshared protocol {name} v{version} from {source_project_id} to {target_project_id}",
            extra={
                "context": {
                    "protocol_name": name,
                    "version": version,
                    "source_project": source_project_id,
                    "target_project": target_project_id,
                }
            },
        )

        return True

    async def list_shared_protocols(self, project_id: str) -> list[dict[str, str]]:
        """List protocols shared with a project.

        Args:
            project_id: Project to list shared protocols for

        Returns:
            List of shared protocol info dicts
        """
        shared = []
        for (source_project, name, version), targets in _shared_protocols.items():
            if project_id in targets:
                shared.append(
                    {
                        "name": name,
                        "version": version,
                        "source_project": source_project,
                    }
                )

        return shared

    async def _get_shared_protocols(
        self,
        project_id: str,
        name: str | None = None,
        version: str | None = None,
    ) -> list[ProtocolDefinition]:
        """Get protocols shared with the specified project.

        Args:
            project_id: Target project
            name: Optional filter by protocol name
            version: Optional filter by protocol version

        Returns:
            List of shared protocol definitions
        """
        shared = []
        for (source_project, proto_name, proto_version), targets in _shared_protocols.items():
            if project_id in targets:
                # Apply filters
                if name and proto_name != name:
                    continue
                if version and proto_version != version:
                    continue

                # Get protocol from source project
                protocol = await self._storage.get_protocol(
                    proto_name, proto_version, source_project
                )
                if protocol:
                    shared.append(protocol)

        return shared

    async def get(
        self, name: str, version: str, project_id: str = "default"
    ) -> ProtocolDefinition | None:
        """Get a protocol definition by name and version.

        Args:
            name: Protocol name
            version: Protocol version
            project_id: Project identifier (defaults to "default")

        Returns:
            ProtocolDefinition if found, None otherwise
        """
        return await self._storage.get_protocol(name, version, project_id)

    async def validate_schema(self, schema: dict) -> ValidationResult:
        """Validate a JSON Schema.

        Args:
            schema: JSON Schema dictionary to validate

        Returns:
            ValidationResult with any validation errors
        """
        errors: list[ProtocolValidationError] = []

        try:
            # Import jsonschema here to avoid hard dependency
            import jsonschema

            # Validate against JSON Schema meta-schema
            jsonschema.Draft7Validator.check_schema(schema)

        except ImportError as e:
            errors.append(
                ProtocolValidationError(
                    path="$",
                    constraint="dependency",
                    expected="jsonschema package",
                    actual="not installed",
                    message=f"jsonschema package required: {e}",
                )
            )
        except jsonschema.SchemaError as e:
            errors.append(
                ProtocolValidationError(
                    path=".".join(str(p) for p in e.path) if e.path else "$",
                    constraint=e.validator,
                    expected=str(e.schema) if hasattr(e, "schema") else "valid",
                    actual=str(e.instance) if hasattr(e, "instance") else "invalid",
                    message=e.message,
                )
            )
        except Exception as e:
            errors.append(
                ProtocolValidationError(
                    path="$",
                    constraint="validation",
                    expected="valid schema",
                    actual=str(type(e)),
                    message=f"Unexpected error: {e}",
                )
            )

        result = ValidationResult(valid=len(errors) == 0, errors=errors)

        if not result.valid:
            logger.warning(
                f"Schema validation failed: {len(errors)} errors",
                extra={"context": {"error_count": len(errors), "errors": errors}},
            )

        return result

    async def check_active_references(
        self, name: str, version: str, project_id: str = "default"
    ) -> list[str]:
        """Check if any sessions reference a protocol version.

        Args:
            name: Protocol name
            version: Protocol version
            project_id: Project identifier (defaults to "default")

        Returns:
            List of session IDs that reference this protocol
        """
        # In production, would query sessions for protocol references
        # For now, return empty list (sessions don't track which protocols they use)
        # This would need to be enhanced by tracking protocol usage in sessions
        return []

    async def can_delete_protocol(
        self, name: str, version: str, project_id: str = "default"
    ) -> tuple[bool, str | None]:
        """Check if a protocol can be safely deleted.

        Args:
            name: Protocol name
            version: Protocol version
            project_id: Project identifier (defaults to "default")

        Returns:
            Tuple of (can_delete, error_message)
        """
        # Check if protocol exists
        protocol = await self._storage.get_protocol(name, version, project_id)
        if not protocol:
            return (
                False,
                f"Protocol '{name}' version '{version}' not found in project '{project_id}'",
            )

        # Check for active references
        active_sessions = await self.check_active_references(name, version, project_id)
        if active_sessions:
            return (
                False,
                f"Cannot delete protocol with {len(active_sessions)} active reference(s): "
                f"{', '.join(active_sessions[:3])}" + ("..." if len(active_sessions) > 3 else ""),
            )

        return True, None
