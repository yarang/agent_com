"""
Unit tests for Protocol Registry component.

Tests protocol registration, discovery, validation,
and duplicate prevention.
"""

import pytest

from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.storage.memory import InMemoryStorage


class TestProtocolRegistry:
    """Tests for ProtocolRegistry class."""

    async def test_register_protocol(
        self, protocol_definition: ProtocolDefinition
    ) -> None:
        """Test registering a new protocol."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        info = await registry.register(protocol_definition)

        assert info.name == "chat_message"
        assert info.version == "1.0.0"
        assert info.registered_at is not None
        assert "point_to_point" in info.capabilities

    async def test_register_duplicate_protocol(
        self, protocol_definition: ProtocolDefinition
    ) -> None:
        """Test duplicate protocol is rejected."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        await registry.register(protocol_definition)

        with pytest.raises(ValueError, match="already exists"):
            await registry.register(protocol_definition)

    async def test_discover_all_protocols(
        self, protocol_definition: ProtocolDefinition
    ) -> None:
        """Test discovering all protocols."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        await registry.register(protocol_definition)

        protocols = await registry.discover()
        assert len(protocols) == 1
        assert protocols[0].name == "chat_message"

    async def test_discover_by_name(
        self, protocol_definition: ProtocolDefinition, sample_protocol_schema: dict
    ) -> None:
        """Test discovering protocols by name."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        await registry.register(protocol_definition)

        # Add another protocol
        other_protocol = ProtocolDefinition(
            name="file_transfer",
            version="2.0.0",
            message_schema=sample_protocol_schema,
            capabilities=["point_to_point"],
        )
        await registry.register(other_protocol)

        protocols = await registry.discover(name="chat_message")
        assert len(protocols) == 1
        assert protocols[0].name == "chat_message"

    async def test_discover_by_tags(
        self, protocol_definition: ProtocolDefinition
    ) -> None:
        """Test discovering protocols by tags."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        await registry.register(protocol_definition)

        protocols = await registry.discover(tags=["chat"])
        assert len(protocols) == 1

    async def test_get_protocol(
        self, protocol_definition: ProtocolDefinition
    ) -> None:
        """Test getting specific protocol."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        await registry.register(protocol_definition)

        protocol = await registry.get("chat_message", "1.0.0")
        assert protocol is not None
        assert protocol.name == "chat_message"

    async def test_validate_schema_valid(self) -> None:
        """Test validating a valid JSON Schema."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        valid_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        result = await registry.validate_schema(valid_schema)
        assert result.valid is True
        assert len(result.errors) == 0

    async def test_validate_schema_invalid(self) -> None:
        """Test validating an invalid JSON Schema."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        invalid_schema = {"type": "invalid_type"}

        result = await registry.validate_schema(invalid_schema)
        assert result.valid is False
        assert len(result.errors) > 0

    async def test_check_active_references(self) -> None:
        """Test checking for active protocol references."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Currently returns empty list (sessions don't track protocol usage)
        active_sessions = await registry.check_active_references("chat_message", "1.0.0")

        assert active_sessions == []

    async def test_can_delete_protocol_exists(self) -> None:
        """Test checking if protocol can be deleted when it exists."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocol = ProtocolDefinition(
            name="test_protocol",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {},
            },
            capabilities=["point_to_point"],
        )

        await registry.register(protocol)

        can_delete, error = await registry.can_delete_protocol("test_protocol", "1.0.0")

        assert can_delete is True
        assert error is None

    async def test_can_delete_protocol_not_exists(self) -> None:
        """Test checking if protocol can be deleted when it doesn't exist."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        can_delete, error = await registry.can_delete_protocol("nonexistent", "1.0.0")

        assert can_delete is False
        assert "not found" in error.lower()

    async def test_discover_with_version_filter(self) -> None:
        """Test discovering protocols with version filter."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocol = ProtocolDefinition(
            name="chat_message",
            version="2.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {},
            },
            capabilities=["point_to_point"],
        )

        await registry.register(protocol)

        protocols = await registry.discover(version="2.0.0")
        assert len(protocols) == 1
        assert protocols[0].version == "2.0.0"

    async def test_discover_no_matches(self) -> None:
        """Test discovering with no matches."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocols = await registry.discover(name="nonexistent")

        assert len(protocols) == 0

    async def test_get_nonexistent_protocol(self) -> None:
        """Test getting non-existent protocol."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocol = await registry.get("nonexistent", "1.0.0")

        assert protocol is None
