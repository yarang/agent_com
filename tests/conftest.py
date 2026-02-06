"""
Pytest configuration and shared fixtures for MCP Broker Server tests.

This module provides common fixtures used across unit, integration,
and load tests to ensure consistent test setup and data.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent_comm_core.db.base import Base

# Agent and Task persistence models
from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.task import TaskDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.communication import (
    Communication,
    CommunicationDirection,
)
from agent_comm_core.models.meeting import (
    Meeting,
    MeetingMessage,
)
from agent_comm_core.models.status import (
    AgentInfo,
    AgentRegistration,
)
from agent_comm_core.services.communication import CommunicationService
from agent_comm_core.services.meeting import MeetingService
from communication_server.api.status import StatisticsService
from communication_server.services.agent_registry import AgentRegistry
from communication_server.websocket.manager import ConnectionManager
from mcp_broker.client.http_client import HTTPClient
from mcp_broker.core.config import BrokerConfig
from mcp_broker.core.logging import setup_logging
from mcp_broker.mcp.meeting_tools import MeetingMCPTools
from mcp_broker.models.message import Message, MessageHeaders
from mcp_broker.models.protocol import ProtocolDefinition, ProtocolMetadata
from mcp_broker.models.session import Session, SessionCapabilities

# =============================================================================
# Configuration
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def configure_logging() -> None:
    """Configure logging for all tests."""
    setup_logging(level="INFO", format_type="text")


# Test database URL - can be overridden by environment
# Default to SQLite for easier local testing
# Use file-based DB instead of :memory: for better test isolation
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///.test_db.sqlite3",
)


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine.

    This fixture creates an engine, runs migrations/creates tables,
    and yields the engine. After the test, it drops all tables.
    """
    import os
    import tempfile

    # Check if using SQLite
    is_sqlite = TEST_DATABASE_URL.startswith("sqlite+")

    if is_sqlite:
        # Create a temporary file for SQLite database
        # This ensures each test gets a fresh database
        fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)

        # Use the temporary file path
        db_url = f"sqlite+aiosqlite:///{db_path}"

        # SQLite doesn't support connection pooling features
        engine = create_async_engine(
            db_url,
            echo=False,
        )
    else:
        # PostgreSQL and other databases support pooling
        engine = create_async_engine(
            TEST_DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        db_path = None

    # Drop all existing tables first (clean slate)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Create all tables (checkfirst to handle existing schema issues)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    yield engine

    # Clean up - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Clean up temp file if it exists
    if db_path and os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """Create a test database session.

    This fixture creates a session, yields it for use in tests,
    and rolls back all changes after the test.
    """
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        # Rollback to keep tests isolated
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def clean_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession]:
    """Clean database before and after tests.

    This fixture deletes all data from tables before and after tests.
    """
    # Get all table classes
    from communication_server.db.communication import CommunicationDB
    from communication_server.db.meeting import (
        DecisionDB,
        MeetingDB,
        MeetingMessageDB,
        MeetingParticipantDB,
    )

    # Delete all data before
    await db_session.execute(delete(CommunicationDB))
    await db_session.execute(delete(MeetingMessageDB))
    await db_session.execute(delete(MeetingParticipantDB))
    await db_session.execute(delete(DecisionDB))
    await db_session.execute(delete(MeetingDB))
    await db_session.commit()

    yield db_session

    # Delete all data after
    await db_session.execute(delete(CommunicationDB))
    await db_session.execute(delete(MeetingMessageDB))
    await db_session.execute(delete(MeetingParticipantDB))
    await db_session.execute(delete(DecisionDB))
    await db_session.execute(delete(MeetingDB))
    await db_session.commit()


# =============================================================================
# Sample Agent Data Fixtures
# =============================================================================


@pytest.fixture
def sample_agent_ids() -> list[str]:
    """Sample agent IDs for testing."""
    return [
        "agent-001",
        "agent-002",
        "agent-003",
        "agent-004",
    ]


@pytest.fixture
def sample_agent_registrations() -> list[AgentRegistration]:
    """Sample agent registration data."""
    return [
        AgentRegistration(
            full_id=str(uuid4()),
            nickname="Alpha",
            capabilities=["text-generation", "analysis"],
        ),
        AgentRegistration(
            full_id=str(uuid4()),
            nickname="Beta",
            capabilities=["code-generation", "debugging"],
        ),
        AgentRegistration(
            full_id=str(uuid4()),
            nickname="Gamma",
            capabilities=["planning", "coordination"],
        ),
    ]


@pytest.fixture
async def registered_agents(
    agent_registry: AgentRegistry,
    sample_agent_registrations: list[AgentRegistration],
) -> list[AgentInfo]:
    """Register sample agents and return their info."""
    agents = []
    for reg in sample_agent_registrations:
        agent = await agent_registry.register_agent(
            full_id=reg.full_id,
            nickname=reg.nickname,
            capabilities=reg.capabilities,
        )
        agents.append(agent)
    return agents


# =============================================================================
# Meeting Fixture
# =============================================================================


@pytest_asyncio.fixture
async def sample_meeting(clean_db: AsyncSession, sample_agent_ids: list[str]) -> Meeting:
    """Create a sample meeting for testing."""
    from communication_server.repositories.meeting import SQLALchemyMeetingRepository

    repo = SQLALchemyMeetingRepository(clean_db)
    service = MeetingService(repo)

    meeting = await service.create_meeting(
        title="Test Meeting",
        participant_ids=sample_agent_ids[:3],
        description="A test meeting for integration tests",
        agenda=["Item 1", "Item 2"],
        max_duration_seconds=3600,
    )

    await clean_db.commit()
    await clean_db.refresh(meeting)

    return meeting


@pytest_asyncio.fixture
async def active_meeting(sample_meeting: Meeting, clean_db: AsyncSession) -> Meeting:
    """Create and start an active meeting."""
    from communication_server.repositories.meeting import SQLALchemyMeetingRepository

    repo = SQLALchemyMeetingRepository(clean_db)
    service = MeetingService(repo)

    meeting = await service.start_meeting(sample_meeting.id)
    await clean_db.commit()
    await clean_db.refresh(meeting)

    return meeting


# =============================================================================
# Communication Server Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def communication_server(clean_db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Create an AsyncClient for testing the Communication Server API.

    This fixture starts the FastAPI app and yields an httpx AsyncClient.
    """
    from communication_server.main import app

    # Create transport for testing
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def communication_service(clean_db: AsyncSession) -> CommunicationService:
    """Create a CommunicationService instance."""
    from communication_server.repositories.communication import (
        SQLAlchemyCommunicationRepository,
    )

    repo = SQLAlchemyCommunicationRepository(clean_db)
    return CommunicationService(repo)


@pytest_asyncio.fixture
async def meeting_service(clean_db: AsyncSession) -> MeetingService:
    """Create a MeetingService instance."""
    from communication_server.repositories.meeting import SQLALchemyMeetingRepository

    repo = SQLALchemyMeetingRepository(clean_db)
    return MeetingService(repo)


@pytest.fixture
def agent_registry() -> AgentRegistry:
    """Create a fresh AgentRegistry instance."""
    return AgentRegistry(inactive_timeout_seconds=300)


@pytest.fixture
def connection_manager() -> ConnectionManager:
    """Create a fresh ConnectionManager instance."""
    return ConnectionManager()


@pytest.fixture
def statistics_service(clean_db: AsyncSession) -> StatisticsService:
    """Create a StatisticsService instance."""
    from communication_server.repositories.communication import (
        SQLAlchemyCommunicationRepository,
    )
    from communication_server.repositories.meeting import SQLALchemyMeetingRepository

    comm_repo = SQLAlchemyCommunicationRepository(clean_db)
    meeting_repo = SQLALchemyMeetingRepository(clean_db)
    return StatisticsService(comm_repo, meeting_repo)


# =============================================================================
# MCP Broker Fixtures
# =============================================================================


@pytest.fixture
def broker_config() -> BrokerConfig:
    """Get test configuration with in-memory storage."""
    return BrokerConfig(
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        storage_backend="memory",
        queue_capacity=100,
        heartbeat_interval=30,
        stale_threshold=30,
        disconnect_threshold=60,
        max_payload_size_mb=10,
        enable_auth=False,
    )


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[HTTPClient]:
    """Create an HTTPClient for Communication Server."""
    client = HTTPClient(base_url="http://test", timeout=30.0)
    await client.ensure_client()
    yield client
    await client.close()


@pytest.fixture
def meeting_mcp_tools(http_client: HTTPClient) -> MeetingMCPTools:
    """Create MeetingMCPTools instance."""
    return MeetingMCPTools(http_client, agent_id="test-agent")


# =============================================================================
# Sample Communications Fixture
# =============================================================================


@pytest_asyncio.fixture
async def sample_communications(
    clean_db: AsyncSession,
    sample_agent_ids: list[str],
    communication_service: CommunicationService,
) -> list[Communication]:
    """Create sample communications for testing."""
    communications = []

    # Create various communications
    test_data = [
        (
            sample_agent_ids[0],
            sample_agent_ids[1],
            "question",
            "How should we implement the API?",
            CommunicationDirection.OUTBOUND,
        ),
        (
            sample_agent_ids[1],
            sample_agent_ids[0],
            "answer",
            "We should use FastAPI with async support",
            CommunicationDirection.INBOUND,
        ),
        (
            sample_agent_ids[0],
            sample_agent_ids[2],
            "proposal",
            "I propose using PostgreSQL for the database",
            CommunicationDirection.OUTBOUND,
        ),
        (
            sample_agent_ids[2],
            sample_agent_ids[0],
            "question",
            "What about the caching layer?",
            CommunicationDirection.INBOUND,
        ),
        (
            sample_agent_ids[1],
            sample_agent_ids[2],
            "notification",
            "The deployment is complete",
            CommunicationDirection.INTERNAL,
        ),
    ]

    for from_agent, to_agent, msg_type, content, direction in test_data:
        comm = await communication_service.log_communication(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=msg_type,
            content=content,
            direction=direction,
            metadata={"test": True},
        )
        communications.append(comm)

    await clean_db.commit()
    return communications


# =============================================================================
# Sample Messages for Meeting
# =============================================================================


@pytest_asyncio.fixture
async def sample_meeting_messages(
    clean_db: AsyncSession,
    active_meeting: Meeting,
    sample_agent_ids: list[str],
    meeting_service: MeetingService,
) -> list[MeetingMessage]:
    """Create sample meeting messages for testing."""
    messages = []

    test_messages = [
        (sample_agent_ids[0], "I think we should start with the API design"),
        (sample_agent_ids[1], "Agreed, what are the key endpoints?"),
        (sample_agent_ids[2], "We need CRUD for users, meetings, and communications"),
        (sample_agent_ids[0], "Let's also consider WebSocket support for real-time updates"),
        (sample_agent_ids[1], "Good point, we'll add that to the agenda"),
    ]

    for agent_id, content in test_messages:
        message = await meeting_service.record_message(
            meeting_id=active_meeting.id,
            agent_id=agent_id,
            content=content,
            message_type="statement",
        )
        messages.append(message)

    await clean_db.commit()
    return messages


# =============================================================================
# Protocol fixtures
# =============================================================================


@pytest.fixture
def sample_protocol_schema() -> dict[str, Any]:
    """Sample JSON Schema for protocol definition."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
        "required": ["text"],
        "additionalProperties": False,
    }


@pytest.fixture
def protocol_definition(sample_protocol_schema: dict[str, Any]) -> ProtocolDefinition:
    """Sample protocol definition for testing."""
    return ProtocolDefinition(
        name="chat_message",
        version="1.0.0",
        message_schema=sample_protocol_schema,
        capabilities=["point_to_point", "broadcast"],
        metadata=ProtocolMetadata(
            author="Test Author",
            description="Chat message protocol",
            tags=["chat", "messaging"],
        ),
    )


# =============================================================================
# Session fixtures
# =============================================================================


@pytest.fixture
def session_capabilities() -> SessionCapabilities:
    """Sample session capabilities."""
    return SessionCapabilities(
        supported_protocols={
            "chat_message": ["1.0.0", "1.1.0"],
            "file_transfer": ["2.0.0"],
        },
        supported_features=["point_to_point", "broadcast", "encryption"],
    )


@pytest.fixture
def active_session(session_capabilities: SessionCapabilities) -> Session:
    """Active session fixture."""
    return Session(
        session_id=uuid4(),
        connection_time=datetime.now(UTC),
        last_heartbeat=datetime.now(UTC),
        status="active",
        capabilities=session_capabilities,
    )


# =============================================================================
# Message fixtures
# =============================================================================


@pytest.fixture
def message_headers() -> MessageHeaders:
    """Sample message headers."""
    return MessageHeaders(priority="normal", ttl=300)


@pytest.fixture
def chat_message(active_session: Session) -> Message:
    """Sample chat message."""
    other_session_id = uuid4()
    return Message(
        sender_id=active_session.session_id,
        recipient_id=other_session_id,
        protocol_name="chat_message",
        protocol_version="1.0.0",
        payload={"text": "Hello, World!", "timestamp": datetime.now(UTC).isoformat()},
        headers=MessageHeaders(priority="normal"),
    )


# =============================================================================
# Async event loop fixture
# =============================================================================


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Mock fixtures
# =============================================================================


@pytest.fixture
def mock_storage() -> MagicMock:
    """Mock storage backend for testing."""
    storage = MagicMock()
    storage.get_protocol = AsyncMock(return_value=None)
    storage.save_protocol = AsyncMock()
    storage.get_session = AsyncMock(return_value=None)
    storage.save_session = AsyncMock()
    storage.enqueue_message = AsyncMock()
    storage.dequeue_messages = AsyncMock(return_value=[])
    storage.delete_session = AsyncMock()
    storage.list_sessions = AsyncMock(return_value=[])
    return storage


# =============================================================================
# Helper fixtures for time-based tests
# =============================================================================


@pytest.fixture
def frozen_time() -> datetime:
    """A fixed time for time-sensitive tests."""
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def time_machine(frozen_time: datetime) -> Generator[datetime]:
    """Yield a frozen time that can be used for testing.

    This is a conceptual fixture - actual time freezing would require
    freezegun or similar library.
    """
    yield frozen_time
    # Time would "unfreeze" here in real implementation


# =============================================================================
# Agent and Task Persistence Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_project_with_owner(clean_db: AsyncSession) -> ProjectDB:
    """Create a test project with owner for Agent/Task testing.

    This fixture is shared across integration and E2E tests for
    SPEC-AGENT-PERSISTENCE-001.
    """
    from uuid import uuid4

    # Create UserDB first (required by foreign key constraint)
    from agent_comm_core.db.models.user import UserDB

    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"testuser_{user_id.hex[:8]}",
        email=f"test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    # Then create ProjectDB
    project_id = f"test-project-{user_id.hex[:8]}"
    project = ProjectDB(
        id=uuid4(),
        project_id=project_id,  # Human-readable unique ID
        name="Test Project for Agents and Tasks",
        description="Test project for Agent and Task persistence testing",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()
    await clean_db.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_agent_for_project(
    clean_db: AsyncSession, test_project_with_owner: ProjectDB
) -> AgentDB:
    """Create a test agent for task assignment.

    This fixture provides a default agent that can be used for
    task assignment tests.
    """
    from uuid import uuid4

    agent = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Test Agent",
        nickname="Tester",
        agent_type="generic",
        status="offline",
        capabilities=["test"],
        is_active=True,
    )
    clean_db.add(agent)
    await clean_db.commit()
    await clean_db.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def test_task_for_project(
    clean_db: AsyncSession, test_project_with_owner: ProjectDB
) -> TaskDB:
    """Create a test task for testing.

    This fixture provides a default pending task that can be used
    for testing task operations.
    """
    from uuid import uuid4

    task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Test Task",
        description="Default test task",
        status="pending",
        priority="medium",
        created_by=test_project_with_owner.owner_id,
        dependencies=[],
    )
    clean_db.add(task)
    await clean_db.commit()
    await clean_db.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_user_for_project(test_project_with_owner: ProjectDB) -> User:
    """Create a test user for API authentication.

    This fixture creates a User object matching the project owner
    for use in authenticated API requests.
    """
    return User(
        id=test_project_with_owner.owner_id,
        email="test@example.com",
        name="Test User",
        is_superuser=False,
    )
