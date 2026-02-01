"""
Pydantic models for protocol-related data structures.

This module defines the data models for communication protocols,
including protocol definitions, validation results, and metadata.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProtocolMetadata(BaseModel):
    """Optional metadata for protocol definitions.

    Attributes:
        author: Protocol author name
        description: Human-readable description
        tags: List of searchable tags
    """

    author: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class ProtocolDefinition(BaseModel):
    """Complete protocol definition with schema and capabilities.

    Attributes:
        name: Protocol identifier in snake_case
        version: Semantic version string (e.g., "1.0.0")
        message_schema: JSON Schema for message validation
        capabilities: Supported communication patterns
        metadata: Optional protocol metadata
    """

    name: str = Field(
        pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$",
        description="Protocol identifier in snake_case",
    )
    version: str = Field(
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
        description="Semantic version (major.minor.patch)",
    )
    message_schema: dict = Field(
        description="JSON Schema for message validation",
        json_schema_extra={"examples": [{"type": "object"}]},
    )
    capabilities: list[
        Literal["point_to_point", "broadcast", "request_response", "streaming"]
    ] = Field(default_factory=list)
    metadata: ProtocolMetadata | None = None

    @field_validator("message_schema")
    @classmethod
    def validate_json_schema(cls, v: dict) -> dict:
        """Validate that the schema is a valid JSON Schema.

        Args:
            v: Schema dictionary to validate

        Returns:
            The validated schema

        Raises:
            ValueError: If schema is invalid
        """
        import jsonschema

        try:
            # Validate against JSON Schema meta-schema
            jsonschema.Draft7Validator.check_schema(v)
            return v
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e.message}") from e

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: list[str]) -> list[str]:
        """Validate capabilities are unique and supported.

        Args:
            v: List of capabilities

        Returns:
            Deduplicated capabilities

        Raises:
            ValueError: If capability is not supported
        """
        valid_capabilities = {
            "point_to_point",
            "broadcast",
            "request_response",
            "streaming",
        }

        for cap in v:
            if cap not in valid_capabilities:
                raise ValueError(
                    f"Invalid capability '{cap}'. "
                    f"Must be one of: {', '.join(sorted(valid_capabilities))}"
                )

        return list(set(v))


class ProtocolInfo(BaseModel):
    """Public information about a registered protocol.

    Attributes:
        name: Protocol identifier
        version: Protocol version
        registered_at: Registration timestamp
        capabilities: Supported communication patterns
        metadata: Optional protocol metadata
    """

    name: str
    version: str
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    capabilities: list[str] = Field(default_factory=list)
    metadata: ProtocolMetadata | None = None


class ProtocolValidationError(BaseModel):
    """Detailed validation error for protocol schemas.

    Attributes:
        path: JSON path to the error location
        constraint: Type of constraint that failed
        expected: Expected value(s)
        actual: Actual value received
        message: Human-readable error message (optional)
    """

    path: str
    constraint: str
    expected: str
    actual: str | None = None
    message: str | None = None


class ValidationResult(BaseModel):
    """Result of protocol validation.

    Attributes:
        valid: Whether validation passed
        errors: List of validation errors (if any)
    """

    valid: bool
    errors: list[ProtocolValidationError] = Field(default_factory=list)
