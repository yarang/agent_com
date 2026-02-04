"""
Characterization tests for Milestone 3 Component Enhancement.

These tests capture the EXISTING behavior of components with project scoping
before implementing Milestone 3 enhancements. They document what the code
currently does, not what it should do.

Purpose: Ensure behavior preservation during Milestone 3 implementation.
"""

from uuid import uuid4

from mcp_broker.models.message import Message
from mcp_broker.models.protocol import ProtocolDefinition
from mcp_broker.models.session import Session, SessionCapabilities
from mcp_broker.negotiation.negotiator import CapabilityNegotiator
from mcp_broker.protocol.registry import ProtocolRegistry
from mcp_broker.routing.router import MessageRouter
from mcp_broker.session.manager import SessionManager
from mcp_broker.storage.memory import InMemoryStorage


class TestProtocolRegistryCharacterization:
    """Characterization tests for ProtocolRegistry with project scoping."""

    async def test_characterize_register_with_default_project(self) -> None:
        """CHARACTERIZE: Protocol registration with default project."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocol = ProtocolDefinition(
            name="chat_protocol",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"message": {"type": "string"}},
            },
            capabilities=["point_to_point"],
        )

        # Register with default project
        info = await registry.register(protocol)

        # Characterize actual behavior
        assert info.name == "chat_protocol"
        assert info.version == "1.0.0"
        assert info.registered_at is not None

        # Verify it's retrievable with default project
        retrieved = await registry.get("chat_protocol", "1.0.0")
        assert retrieved is not None
        assert retrieved.name == "chat_protocol"

    async def test_characterize_register_with_explicit_project(self) -> None:
        """CHARACTERIZE: Protocol registration with explicit project_id."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        protocol = ProtocolDefinition(
            name="file_protocol",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"filename": {"type": "string"}},
            },
            capabilities=["point_to_point"],
        )

        # Register with custom project
        info = await registry.register(protocol, project_id="project_a")

        # Characterize actual behavior
        assert info.name == "file_protocol"

        # Verify it's NOT retrievable from default project
        default_retrieved = await registry.get("file_protocol", "1.0.0", project_id="default")
        assert default_retrieved is None

        # Verify it IS retrievable from project_a
        project_a_retrieved = await registry.get("file_protocol", "1.0.0", project_id="project_a")
        assert project_a_retrieved is not None

    async def test_characterize_protocol_isolation_between_projects(self) -> None:
        """CHARACTERIZE: Protocols are isolated between projects."""
        storage = InMemoryStorage()
        registry = ProtocolRegistry(storage)

        # Register same protocol in two projects
        protocol_a = ProtocolDefinition(
            name="shared_protocol",
            version="1.0.0",
            message_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            capabilities=["point_to_point"],
        )

        await registry.register(protocol_a, project_id="project_a")
        await registry.register(protocol_a, project_id="project_b")

        # Characterize: Each project has its own protocol
        protocols_a = await registry.discover(project_id="project_a")
        protocols_b = await registry.discover(project_id="project_b")

        assert len(protocols_a) == 1
        assert len(protocols_b) == 1
        assert protocols_a[0].name == "shared_protocol"
        assert protocols_b[0].name == "shared_protocol"


class TestSessionManagerCharacterization:
    """Characterization tests for SessionManager with project scoping."""

    async def test_characterize_create_session_with_default_project(self) -> None:
        """CHARACTERIZE: Session creation with default project."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create session without explicit project_id
        session = await manager.create_session(capabilities)

        # Characterize actual behavior
        assert session.session_id is not None
        assert session.project_id == "default"
        assert session.status == "active"

    async def test_characterize_create_session_with_explicit_project(self) -> None:
        """CHARACTERIZE: Session creation with explicit project_id."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create session with custom project
        session = await manager.create_session(capabilities, project_id="project_a")

        # Characterize actual behavior
        assert session.project_id == "project_a"

    async def test_characterize_session_isolation_between_projects(self) -> None:
        """CHARACTERIZE: Sessions are isolated between projects."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create sessions in different projects
        session_a = await manager.create_session(capabilities, project_id="project_a")
        session_b = await manager.create_session(capabilities, project_id="project_b")

        # Characterize: list_sessions respects project boundary
        list_a = await manager.list_sessions(project_id="project_a")
        list_b = await manager.list_sessions(project_id="project_b")

        assert len(list_a) == 1
        assert len(list_b) == 1
        assert list_a[0].session_id == session_a.session_id
        assert list_b[0].session_id == session_b.session_id

    async def test_characterize_cross_project_session_retrieval(self) -> None:
        """CHARACTERIZE: Attempting to retrieve session from different project."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Create session in project_a
        session = await manager.create_session(capabilities, project_id="project_a")

        # Characterize: Retrieving from project_b returns None
        retrieved = await manager.get_session(session.session_id, project_id="project_b")
        assert retrieved is None

        # Characterize: Retrieving from project_a succeeds
        retrieved_correct = await manager.get_session(session.session_id, project_id="project_a")
        assert retrieved_correct is not None


class TestMessageRouterCharacterization:
    """Characterization tests for MessageRouter with project scoping."""

    async def test_characterize_send_within_same_project(self) -> None:
        """CHARACTERIZE: Message delivery within same project."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)
        router = MessageRouter(manager, storage)

        # Create sender and recipient in same project
        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        sender = await manager.create_session(capabilities, project_id="project_a")
        recipient = await manager.create_session(capabilities, project_id="project_a")

        message = Message(
            sender_id=sender.session_id,
            recipient_id=recipient.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Characterize: Message delivery succeeds within same project
        result = await router.send_message(
            sender.session_id,
            recipient.session_id,
            message,
            project_id="project_a",
        )

        assert result.success is True

    async def test_characterize_reject_cross_project_message(self) -> None:
        """CHARACTERIZE: Cross-project message is rejected."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)
        router = MessageRouter(manager, storage)

        # Create sender in project_a, recipient in project_b
        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        sender = await manager.create_session(capabilities, project_id="project_a")
        recipient = await manager.create_session(capabilities, project_id="project_b")

        message = Message(
            sender_id=sender.session_id,
            recipient_id=recipient.session_id,
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Hello"},
        )

        # Characterize: Cross-project message is rejected
        result = await router.send_message(
            sender.session_id,
            recipient.session_id,
            message,
            project_id="project_a",
        )

        assert result.success is False
        assert (
            "cross-project" in result.error_reason.lower()
            or "not found in project" in result.error_reason.lower()
        )

    async def test_characterize_broadcast_within_project(self) -> None:
        """CHARACTERIZE: Broadcast only reaches sessions in same project."""
        storage = InMemoryStorage()
        manager = SessionManager(storage)
        router = MessageRouter(manager, storage)

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["broadcast"],
        )

        # Create sessions in different projects
        sender = await manager.create_session(capabilities, project_id="project_a")
        recipient_a = await manager.create_session(capabilities, project_id="project_a")
        recipient_b = await manager.create_session(capabilities, project_id="project_b")

        message = Message(
            sender_id=sender.session_id,
            recipient_id=None,  # Broadcast
            protocol_name="chat",
            protocol_version="1.0.0",
            payload={"text": "Broadcast"},
        )

        # Characterize: Broadcast only reaches same project
        result = await router.broadcast_message(
            sender.session_id,
            message,
            project_id="project_a",
        )

        # Only recipient_a should receive (same project as sender)
        assert result.success is True
        assert result.delivery_count == 1
        assert recipient_a.session_id in result.recipients.get("delivered", [])
        assert recipient_b.session_id not in result.recipients.get("delivered", [])


class TestCapabilityNegotiatorCharacterization:
    """Characterization tests for CapabilityNegotiator."""

    async def test_characterize_negotiate_same_project_sessions(self) -> None:
        """CHARACTERIZE: Negotiation between sessions with same protocols."""
        negotiator = CapabilityNegotiator()

        capabilities = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        session_a = Session(
            session_id=uuid4(),
            project_id="project_a",
            capabilities=capabilities,
        )
        session_b = Session(
            session_id=uuid4(),
            project_id="project_a",
            capabilities=capabilities,
        )

        # Characterize: Same project, same protocols = compatible
        result = await negotiator.negotiate(session_a, session_b)

        assert result.compatible is True
        assert "chat" in result.supported_protocols

    async def test_characterize_negotiate_blocks_cross_project_by_default(self) -> None:
        """CHARACTERIZE: Negotiator blocks cross-project by default (Milestone 3 enhancement)."""
        negotiator = CapabilityNegotiator()

        capabilities_a = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        capabilities_b = SessionCapabilities(
            supported_protocols={"chat": ["1.0.0"]},
            supported_features=["point_to_point"],
        )

        # Sessions from different projects
        session_a = Session(
            session_id=uuid4(),
            project_id="project_a",
            capabilities=capabilities_a,
        )
        session_b = Session(
            session_id=uuid4(),
            project_id="project_b",  # Different project
            capabilities=capabilities_b,
        )

        # Characterize: NEW behavior - blocks cross-project by default
        result = await negotiator.negotiate(session_a, session_b)

        # Should be incompatible due to cross-project boundary
        assert result.compatible is False
        assert result.cross_project is True
        assert len(result.incompatibilities) > 0
        assert "cross-project" in result.incompatibilities[0].lower()
