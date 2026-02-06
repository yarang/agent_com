"""
End-to-end tests for Agent persistence.

Tests complete agent lifecycle to ensure data persists across
page refreshes (simulated by new database sessions).
"""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.common import AgentStatus

# =============================================================================
# E2E Scenario: Agent Persistence Across Page Refresh (REQ-E-002, REQ-N-003)
# =============================================================================


@pytest.mark.e2e
async def test_agent_persistence_scenario(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Full lifecycle test for agent persistence.

    Given: Empty database
    When:
        1. Create agent via API
        2. Query agent from database
        3. Simulate page refresh (new DB session)
        4. Query agent again
    Then:
        1. Agent data persists correctly
        2. All fields match original values
        3. Agent survives "page refresh" (new session)
    """
    from httpx import ASGITransport

    from agent_comm_core.api.v1.agents import get_db as agents_get_db
    from agent_comm_core.db.models.user import UserDB
    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup: Create user and project
    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"e2e_test_user_{user_id.hex[:8]}",
        email=f"e2e_test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    project = ProjectDB(
        id=uuid4(),
        project_id=f"e2e-test-{user_id.hex[:8]}",
        name="E2E Test Project",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        username="e2e_test_user",
        is_superuser=False,
    )

    # Mock authentication
    async def mock_get_current_user():
        return test_user

    # Mock database dependency
    async def mock_get_db():
        return clean_db

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[agents_get_db] = mock_get_db

    # ============================================================================
    # Step 1: Create agent via API
    # ============================================================================

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        agent_data = {
            "project_id": str(project.id),
            "name": "Persistent Agent",
            "nickname": "Persister",
            "agent_type": "generic",
            "capabilities": ["communicate", "analyze", "persist"],
            "config": {"setting": "value", "number": 42},
        }

        response = await client.post("/api/v1/agents", json=agent_data)
        assert response.status_code == 201

        created_agent = response.json()
        agent_id = UUID(created_agent["id"])

        # Verify initial state
        assert created_agent["name"] == "Persistent Agent"
        assert created_agent["nickname"] == "Persister"
        assert created_agent["capabilities"] == ["communicate", "analyze", "persist"]
        assert created_agent["config"]["setting"] == "value"
        assert created_agent["config"]["number"] == 42
        assert created_agent["status"] == AgentStatus.OFFLINE.value
        assert created_agent["is_active"] is True

    # ============================================================================
    # Step 2: Query agent from database (same session)
    # ============================================================================

    result = await clean_db.execute(select(AgentDB).where(AgentDB.id == agent_id))
    agent_db = result.scalar_one_or_none()

    assert agent_db is not None
    assert agent_db.name == "Persistent Agent"
    assert agent_db.nickname == "Persister"
    assert agent_db.capabilities == ["communicate", "analyze", "persist"]
    assert agent_db.config["setting"] == "value"
    assert agent_db.config["number"] == 42

    # ============================================================================
    # Step 3: Simulate page refresh (new DB session)
    # ============================================================================

    # Create a new database session to simulate page refresh
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        # Query agent from new session
        result = await new_session.execute(select(AgentDB).where(AgentDB.id == agent_id))
        refreshed_agent = result.scalar_one_or_none()

        # Verify agent persists after "refresh"
        assert refreshed_agent is not None
        assert refreshed_agent.id == agent_id
        assert refreshed_agent.name == "Persistent Agent"
        assert refreshed_agent.nickname == "Persister"
        assert refreshed_agent.agent_type == "generic"
        assert refreshed_agent.capabilities == ["communicate", "analyze", "persist"]
        assert refreshed_agent.config["setting"] == "value"
        assert refreshed_agent.config["number"] == 42
        assert refreshed_agent.status == AgentStatus.OFFLINE.value
        assert refreshed_agent.is_active is True

        # Verify timestamps
        assert refreshed_agent.created_at is not None
        assert refreshed_agent.updated_at is not None

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_agent_update_persistence(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test agent updates persist across sessions.

    Given: An existing agent
    When:
        1. Update agent via API
        2. Query from new session (simulated refresh)
    Then: Updated values persist correctly
    """
    from httpx import ASGITransport

    from agent_comm_core.api.v1.agents import get_db as agents_get_db
    from agent_comm_core.db.models.user import UserDB
    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"update_test_user_{user_id.hex[:8]}",
        email=f"update_test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    project = ProjectDB(
        id=uuid4(),
        project_id=f"update-test-{user_id.hex[:8]}",
        name="Update Test Project",
        owner_id=user_id,
    )
    clean_db.add(project)

    agent = AgentDB(
        id=uuid4(),
        project_id=project.id,
        name="Original Name",
        nickname="Original",
        agent_type="generic",
        capabilities=["original"],
        is_active=True,
    )
    clean_db.add(agent)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        username="update_test_user",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    async def mock_get_db():
        return clean_db

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[agents_get_db] = mock_get_db

    # Update agent via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        update_data = {
            "nickname": "Updated Nickname",
            "capabilities": ["updated", "new_capability"],
            "status": "online",
        }

        response = await client.patch(f"/api/v1/agents/{agent.id}", json=update_data)
        assert response.status_code == 200

        updated = response.json()
        assert updated["nickname"] == "Updated Nickname"
        assert updated["capabilities"] == ["updated", "new_capability"]
        assert updated["status"] == "online"

    # Verify persistence in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        result = await new_session.execute(select(AgentDB).where(AgentDB.id == agent.id))
        persisted = result.scalar_one_or_none()

        assert persisted.nickname == "Updated Nickname"
        assert persisted.capabilities == ["updated", "new_capability"]
        assert persisted.status == "online"
        assert persisted.name == "Original Name"  # Unchanged

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_agent_deletion_cascade(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test agent deletion cascades correctly.

    Given: An agent with API keys and participants
    When: Agent is deleted
    Then: Related records are also deleted (CASCADE)
    """
    from httpx import ASGITransport

    from agent_comm_core.api.v1.agents import get_db as agents_get_db
    from agent_comm_core.db.models.agent_api_key import AgentApiKeyDB
    from agent_comm_core.db.models.user import UserDB
    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"cascade_test_user_{user_id.hex[:8]}",
        email=f"cascade_test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    project = ProjectDB(
        id=uuid4(),
        project_id=f"cascade-test-{user_id.hex[:8]}",
        name="Cascade Test Project",
        owner_id=user_id,
    )
    clean_db.add(project)

    agent = AgentDB(
        id=uuid4(),
        project_id=project.id,
        name="Cascade Agent",
        capabilities=[],
    )
    clean_db.add(agent)

    # Create related records
    api_key = AgentApiKeyDB(
        id=uuid4(),
        project_id=project.id,
        agent_id=agent.id,
        key_id=f"test_key_{uuid4().hex[:8]}",
        api_key_hash="test_hash_value",
        key_prefix="sk_agent_v1_test",
        capabilities=[],
        created_by_type="user",
        created_by_id=user_id,
    )
    clean_db.add(api_key)

    await clean_db.commit()

    test_user = User(
        id=user_id,
        username="cascade_test_user",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    async def mock_get_db():
        return clean_db

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[agents_get_db] = mock_get_db

    # Delete agent via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/agents/{agent.id}")
        assert response.status_code == 204

    # Verify cascade in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        # Agent should be deleted
        result = await new_session.execute(select(AgentDB).where(AgentDB.id == agent.id))
        assert result.scalar_one_or_none() is None

        # API key should be cascaded
        result = await new_session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.agent_id == agent.id)
        )
        assert result.scalar_one_or_none() is None

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_agent_status_transition_persistence(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test agent status transitions persist correctly.

    Given: An agent with status transitions
    When: Transitioning through multiple states
    Then: Each status persists correctly
    """
    from httpx import ASGITransport

    from agent_comm_core.api.v1.agents import get_db as agents_get_db
    from agent_comm_core.db.models.user import UserDB
    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"status_test_user_{user_id.hex[:8]}",
        email=f"status_test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    project = ProjectDB(
        id=uuid4(),
        project_id=f"status-test-{user_id.hex[:8]}",
        name="Status Test Project",
        owner_id=user_id,
    )
    clean_db.add(project)

    agent = AgentDB(
        id=uuid4(),
        project_id=project.id,
        name="Status Agent",
        status=AgentStatus.OFFLINE.value,
        capabilities=[],
    )
    clean_db.add(agent)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        username="status_test_user",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    async def mock_get_db():
        return clean_db

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[agents_get_db] = mock_get_db

    # Transition through states
    transitions = [
        ("offline", "online"),
        ("online", "busy"),
        ("busy", "offline"),
        ("offline", "error"),
        ("error", "online"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for from_status, to_status in transitions:
            # Ensure current status matches expected
            result = await clean_db.execute(select(AgentDB).where(AgentDB.id == agent.id))
            current = result.scalar_one()
            assert current.status == from_status, f"Expected {from_status}, got {current.status}"

            # Transition
            response = await client.patch(f"/api/v1/agents/{agent.id}", json={"status": to_status})
            assert response.status_code == 200
            assert response.json()["status"] == to_status

    # Verify final status persists
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        result = await new_session.execute(select(AgentDB).where(AgentDB.id == agent.id))
        final_agent = result.scalar_one()
        assert final_agent.status == "online"

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_multiple_agents_persistence(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test persistence of multiple agents in a project.

    Given: A project with multiple agents
    When: Creating and querying agents
    Then: All agents persist correctly
    """
    from httpx import ASGITransport

    from agent_comm_core.api.v1.agents import get_db as agents_get_db
    from agent_comm_core.db.models.user import UserDB
    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"multi_test_user_{user_id.hex[:8]}",
        email=f"multi_test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    project = ProjectDB(
        id=uuid4(),
        project_id=f"multi-agent-{user_id.hex[:8]}",
        name="Multi-Agent Project",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        username="multi_test_user",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    async def mock_get_db():
        return clean_db

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[agents_get_db] = mock_get_db

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Create multiple agents
    agent_data = [
        {"name": "Agent Alpha", "nickname": "Alpha", "status": "online"},
        {"name": "Agent Beta", "nickname": "Beta", "status": "offline"},
        {"name": "Agent Gamma", "nickname": "Gamma", "status": "busy"},
    ]

    created_ids = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for data in agent_data:
            payload = {
                "project_id": str(project.id),
                **data,
                "capabilities": [],
            }
            response = await client.post("/api/v1/agents", json=payload)
            assert response.status_code == 201
            created_ids.append(UUID(response.json()["id"]))

    # Verify all persist in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        result = await new_session.execute(select(AgentDB).where(AgentDB.project_id == project.id))
        agents = result.scalars().all()

        assert len(agents) == 3
        agent_names = {a.name for a in agents}
        assert agent_names == {"Agent Alpha", "Agent Beta", "Agent Gamma"}

        # Verify each agent's data
        for agent in agents:
            assert agent.id in created_ids
            assert agent.project_id == project.id

    app.dependency_overrides.clear()
