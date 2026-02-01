"""
Unit tests for protocol-related Pydantic models.

Tests the ProtocolDefinition, ProtocolInfo, ProtocolMetadata,
and ValidationResult models for validation and serialization.
"""

import pytest

from mcp_broker.models.protocol import (
    ProtocolDefinition,
    ProtocolInfo,
    ProtocolMetadata,
    ProtocolValidationError,
    ValidationResult,
)


# Sample schema for testing
SAMPLE_PROTOCOL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["text"],
    "additionalProperties": False,
}


class TestProtocolMetadata:
    """Tests for ProtocolMetadata model."""

    def test_create_minimal_metadata(self) -> None:
        """Test creating metadata with no fields."""
        metadata = ProtocolMetadata()
        assert metadata.author is None
        assert metadata.description is None
        assert metadata.tags == []

    def test_create_full_metadata(self) -> None:
        """Test creating metadata with all fields."""
        metadata = ProtocolMetadata(
            author="Test Author",
            description="Test description",
            tags=["tag1", "tag2", "tag3"],
        )
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description"
        assert len(metadata.tags) == 3


class TestProtocolDefinition:
    """Tests for ProtocolDefinition model."""

    def test_create_valid_protocol(self) -> None:
        """Test creating a valid protocol definition."""
        protocol = ProtocolDefinition(
            name="chat_message",
            version="1.0.0",
            message_schema=SAMPLE_PROTOCOL_SCHEMA,
            capabilities=["point_to_point", "broadcast"],
            metadata=ProtocolMetadata(
                author="Test Author",
                description="Chat message protocol",
                tags=["chat", "messaging"],
            ),
        )
        assert protocol.name == "chat_message"
        assert protocol.version == "1.0.0"
        assert protocol.message_schema["type"] == "object"
        assert "point_to_point" in protocol.capabilities
        assert "broadcast" in protocol.capabilities

    def test_name_validation_snake_case(self) -> None:
        """Test protocol name must be snake_case."""
        with pytest.raises(ValueError, match="pattern"):
            ProtocolDefinition(
                name="InvalidName",  # PascalCase
                version="1.0.0",
                message_schema=SAMPLE_PROTOCOL_SCHEMA,
            )

    def test_name_validation_single_word(self) -> None:
        """Test single word protocol name is valid."""
        protocol = ProtocolDefinition(
            name="chat", version="1.0.0", message_schema=SAMPLE_PROTOCOL_SCHEMA
        )
        assert protocol.name == "chat"

    def test_version_validation_semantic(self) -> None:
        """Test version must follow semantic versioning."""
        with pytest.raises(ValueError, match="pattern"):
            ProtocolDefinition(
                name="test_protocol", version="1.0", message_schema=SAMPLE_PROTOCOL_SCHEMA
            )

    def test_version_validation_valid_formats(self) -> None:
        """Test various valid semantic version formats."""
        valid_versions = ["1.0.0", "0.1.0", "10.20.30"]
        for version in valid_versions:
            protocol = ProtocolDefinition(
                name="test_protocol",
                version=version,
                message_schema=SAMPLE_PROTOCOL_SCHEMA,
            )
            assert protocol.version == version

    def test_schema_validation_invalid_json_schema(self) -> None:
        """Test invalid JSON Schema is rejected."""
        with pytest.raises(ValueError, match="Invalid JSON Schema"):
            ProtocolDefinition(
                name="test_protocol",
                version="1.0.0",
                message_schema={"type": "invalid_type"},
            )

    def test_capabilities_deduplication(self) -> None:
        """Test duplicate capabilities are removed."""
        protocol = ProtocolDefinition(
            name="test_protocol",
            version="1.0.0",
            message_schema=SAMPLE_PROTOCOL_SCHEMA,
            capabilities=["point_to_point", "point_to_point", "broadcast"],
        )
        assert len(protocol.capabilities) == 2

    def test_capabilities_invalid_capability(self) -> None:
        """Test invalid capability is rejected."""
        with pytest.raises(ValueError):  # Pydantic validation error
            ProtocolDefinition(
                name="test_protocol",
                version="1.0.0",
                message_schema=SAMPLE_PROTOCOL_SCHEMA,
                capabilities=["invalid_capability"],
            )

    def test_all_valid_capabilities(self) -> None:
        """Test all valid capabilities are accepted."""
        protocol = ProtocolDefinition(
            name="test_protocol",
            version="1.0.0",
            message_schema=SAMPLE_PROTOCOL_SCHEMA,
            capabilities=["point_to_point", "broadcast", "request_response", "streaming"],
        )
        assert len(protocol.capabilities) == 4

    def test_metadata_optional(self) -> None:
        """Test metadata is optional."""
        protocol = ProtocolDefinition(
            name="test_protocol",
            version="1.0.0",
            message_schema=SAMPLE_PROTOCOL_SCHEMA,
        )
        assert protocol.metadata is None

    def test_metadata_included(self) -> None:
        """Test metadata can be included."""
        metadata = ProtocolMetadata(author="Test Author", tags=["test"])
        protocol = ProtocolDefinition(
            name="test_protocol",
            version="1.0.0",
            message_schema=SAMPLE_PROTOCOL_SCHEMA,
            metadata=metadata,
        )
        assert protocol.metadata is not None
        assert protocol.metadata.author == "Test Author"


class TestProtocolInfo:
    """Tests for ProtocolInfo model."""

    def test_create_protocol_info(self) -> None:
        """Test creating protocol info."""
        info = ProtocolInfo(
            name="chat_message",
            version="1.0.0",
            capabilities=["point_to_point"],
        )
        assert info.name == "chat_message"
        assert info.version == "1.0.0"
        assert info.registered_at is not None
        assert "point_to_point" in info.capabilities

    def test_registered_at_defaults_to_now(self) -> None:
        """Test registered_at defaults to current time."""
        info = ProtocolInfo(name="test", version="1.0.0")
        assert info.registered_at is not None


class TestProtocolValidationError:
    """Tests for ProtocolValidationError model."""

    def test_create_validation_error(self) -> None:
        """Test creating validation error."""
        error = ProtocolValidationError(
            path="$.type",
            constraint="enum",
            expected="object, array",
            actual="invalid",
        )
        assert error.path == "$.type"
        assert error.constraint == "enum"
        assert error.expected == "object, array"
        assert error.actual == "invalid"


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_create_valid_result(self) -> None:
        """Test creating valid validation result."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_create_invalid_result(self) -> None:
        """Test creating invalid validation result with errors."""
        errors = [
            ProtocolValidationError(
                path="$.field1", constraint="required", expected="present", actual="missing"
            ),
            ProtocolValidationError(
                path="$.field2", constraint="type", expected="string", actual="number"
            ),
        ]
        result = ValidationResult(valid=False, errors=errors)
        assert result.valid is False
        assert len(result.errors) == 2
