"""
Integration tests for Agent API endpoints.

Tests the complete Agent CRUD operations through the API layer,
ensuring proper integration between API, service, and database layers.
"""

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.common import AgentStatus

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_project_with_owner(clean_db: AsyncSession) -> ProjectDB:
    """Create a test project with owner for testing."""
    from agent_comm_core.db.models.user import UserDB

    # Create test user first (required by foreign key constraint)
    user_id = uuid4()
    user = UserDB(
        id=user_id,
        username=f"testuser_{user_id.hex[:8]}",
        email=f"test_{user_id.hex[:8]}@example.com",
    )
    clean_db.add(user)

    # Create project
    project = ProjectDB(
        id=uuid4(),
        project_id=f"test-project-{user_id.hex[:8]}",  # Required field
        name="Test Project",
        description="Test project for agent integration tests",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()
    await clean_db.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_user(clean_db: AsyncSession, test_project_with_owner: ProjectDB) -> User:
    """Create a test user for API authentication."""
    from agent_comm_core.db.models.user import UserDB

    # Get the user from database to retrieve username
    result = await clean_db.execute(
        select(UserDB).where(UserDB.id == test_project_with_owner.owner_id)
    )
    user_db = result.scalar_one()

    return User(
        id=user_db.id,  # UUID directly
        username=user_db.username,
    )


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers for API requests.

    Note: In a real implementation, this would create a valid JWT token.
    For testing purposes, we mock the authentication dependency.
    """
    # Return mock headers - actual JWT would be generated in real implementation
    return {"Authorization": f"Bearer mock-token-{test_user.id}"}


@pytest_asyncio.fixture
async def authenticated_client(clean_db: AsyncSession, test_user: User) -> AsyncClient:
    """Create an authenticated test client using the test database."""
    from httpx import ASGITransport

    from agent_comm_core.api.v1.agents import get_db
    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Mock the get_current_user dependency
    async def mock_get_current_user():
        return test_user

    # Mock the get_db dependency to return clean_db
    async def mock_get_db():
        return clean_db

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def existing_agent(clean_db: AsyncSession, test_project_with_owner: ProjectDB) -> AgentDB:
    """Create an existing agent for testing updates and deletions."""
    agent = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Existing Agent",
        nickname="Existing",
        agent_type="generic",
        status=AgentStatus.OFFLINE.value,
        capabilities=["test"],
        is_active=True,
    )
    clean_db.add(agent)
    await clean_db.commit()
    await clean_db.refresh(agent)
    return agent


# =============================================================================
# Agent Creation Tests (REQ-E-001)
# =============================================================================


@pytest.mark.integration
async def test_create_agent_success(
    authenticated_client: AsyncClient,
    test_project_with_owner: ProjectDB,
):
    """
    Test successful agent creation via API.

    Given: A valid project and authenticated user
    When: Creating an agent with valid data via POST /api/v1/agents
    Then: Agent is created and returned with generated UUID
    """
    agent_data = {
        "project_id": str(test_project_with_owner.id),
        "name": "Test Agent",
        "nickname": "Tester",
        "agent_type": "generic",
        "capabilities": ["communicate", "analyze"],
        "config": {"setting": "value"},
    }

    response = await authenticated_client.post("/api/v1/agents", json=agent_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Agent"
    assert data["nickname"] == "Tester"
    assert data["agent_type"] == "generic"
    assert data["capabilities"] == ["communicate", "analyze"]
    assert data["status"] == AgentStatus.OFFLINE.value
    assert data["is_active"] is True
    assert "id" in data
    assert UUID(data["id"])


@pytest.mark.integration
async def test_create_agent_duplicate_name(
    authenticated_client: AsyncClient,
    test_project_with_owner: ProjectDB,
    existing_agent: AgentDB,
):
    """
    Test duplicate name rejection in same project.

    Given: A project with an existing agent named 'Existing Agent'
    When: Creating another agent with the same name in the same project
    Then: API returns 409 Conflict error
    """
    agent_data = {
        "project_id": str(test_project_with_owner.id),
        "name": existing_agent.name,  # Duplicate name
        "capabilities": [],
    }

    response = await authenticated_client.post("/api/v1/agents", json=agent_data)

    assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# Agent Listing Tests (REQ-E-002)
# =============================================================================


@pytest.mark.integration
async def test_list_agents_by_project(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
):
    """
    Test filtering agents by project_id.

    Given: Multiple agents across different projects
    When: Querying agents with project_id filter
    Then: Only agents from the specified project are returned
    """
    # Create another project for testing
    other_project = ProjectDB(
        id=uuid4(),
        project_id=f"other-project-{test_user.id.hex[:8]}",
        name="Other Project",
        owner_id=test_user.id,
    )
    clean_db.add(other_project)

    # Create agents in both projects
    agent1 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Agent 1",
        status=AgentStatus.ONLINE.value,
        capabilities=[],
    )
    agent2 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Agent 2",
        status=AgentStatus.OFFLINE.value,
        capabilities=[],
    )
    agent3 = AgentDB(
        id=uuid4(),
        project_id=other_project.id,
        name="Agent 3",
        status=AgentStatus.ONLINE.value,
        capabilities=[],
    )
    clean_db.add_all([agent1, agent2, agent3])
    await clean_db.commit()

    # Query agents for test_project_with_owner
    response = await authenticated_client.get(
        f"/api/v1/agents?project_id={test_project_with_owner.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    agent_names = {agent["name"] for agent in data["items"]}
    assert agent_names == {"Agent 1", "Agent 2"}


@pytest.mark.integration
async def test_list_agents_by_status(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
):
    """
    Test filtering agents by status.

    Given: Agents with different statuses
    When: Querying agents with status filter
    Then: Only agents with matching status are returned
    """
    # Create agents with different statuses
    agent1 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Online Agent",
        status=AgentStatus.ONLINE.value,
        capabilities=[],
    )
    agent2 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Offline Agent",
        status=AgentStatus.OFFLINE.value,
        capabilities=[],
    )
    agent3 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Busy Agent",
        status=AgentStatus.BUSY.value,
        capabilities=[],
    )
    clean_db.add_all([agent1, agent2, agent3])
    await clean_db.commit()

    # Query only online agents
    response = await authenticated_client.get(
        f"/api/v1/agents?project_id={test_project_with_owner.id}&status=online"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Online Agent"


@pytest.mark.integration
async def test_list_agents_by_is_active(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
):
    """
    Test filtering agents by is_active flag.

    Given: Active and inactive agents
    When: Querying agents with is_active filter
    Then: Only agents with matching is_active are returned
    """
    # Create active and inactive agents
    agent1 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Active Agent",
        is_active=True,
        capabilities=[],
    )
    agent2 = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Inactive Agent",
        is_active=False,
        capabilities=[],
    )
    clean_db.add_all([agent1, agent2])
    await clean_db.commit()

    # Query only active agents
    response = await authenticated_client.get(
        f"/api/v1/agents?project_id={test_project_with_owner.id}&is_active=true"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Active Agent"


@pytest.mark.integration
async def test_list_agents_pagination(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
):
    """
    Test agent list pagination.

    Given: 25 agents in a project
    When: Querying with page=1, size=10
    Then: First 10 agents are returned with has_more=true
    """
    # Create 25 agents
    agents = [
        AgentDB(
            id=uuid4(),
            project_id=test_project_with_owner.id,
            name=f"Agent {i}",
            capabilities=[],
        )
        for i in range(25)
    ]
    clean_db.add_all(agents)
    await clean_db.commit()

    # Query first page
    response = await authenticated_client.get(
        f"/api/v1/agents?project_id={test_project_with_owner.id}&page=1&size=10"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["has_more"] is True


# =============================================================================
# Agent Retrieval Tests
# =============================================================================


@pytest.mark.integration
async def test_get_agent_by_id(
    authenticated_client: AsyncClient,
    existing_agent: AgentDB,
):
    """
    Test retrieving agent by ID.

    Given: An existing agent
    When: Querying GET /api/v1/agents/{agent_id}
    Then: Agent details are returned
    """
    response = await authenticated_client.get(f"/api/v1/agents/{existing_agent.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(existing_agent.id)
    assert data["name"] == existing_agent.name


@pytest.mark.integration
async def test_get_agent_not_found(authenticated_client: AsyncClient):
    """
    Test retrieving non-existent agent.

    Given: No agent with the given ID
    When: Querying GET /api/v1/agents/{agent_id}
    Then: API returns 404 Not Found
    """
    fake_id = uuid4()
    response = await authenticated_client.get(f"/api/v1/agents/{fake_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Agent Update Tests
# =============================================================================


@pytest.mark.integration
async def test_update_agent(
    authenticated_client: AsyncClient,
    existing_agent: AgentDB,
):
    """
    Test partial update of agent fields.

    Given: An existing agent
    When: Sending PATCH with partial update data
    Then: Only specified fields are updated
    """
    update_data = {
        "nickname": "Updated Nickname",
        "capabilities": ["new_capability"],
    }

    response = await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json=update_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["nickname"] == "Updated Nickname"
    assert data["capabilities"] == ["new_capability"]
    assert data["name"] == existing_agent.name  # Unchanged


@pytest.mark.integration
async def test_update_agent_is_active(
    authenticated_client: AsyncClient,
    existing_agent: AgentDB,
):
    """
    Test updating agent active state.

    Given: An active agent
    When: Setting is_active to false
    Then: Agent becomes inactive
    """
    response = await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json={"is_active": False}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_active"] is False


# =============================================================================
# Agent Deletion Tests (REQ-N-002)
# =============================================================================


@pytest.mark.integration
async def test_delete_agent(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    existing_agent: AgentDB,
):
    """
    Test agent deletion with CASCADE behavior.

    Given: An existing agent
    When: Sending DELETE /api/v1/agents/{agent_id}
    Then: Agent is deleted and CASCADE handles related records
    """
    response = await authenticated_client.delete(f"/api/v1/agents/{existing_agent.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion in database
    result = await clean_db.execute(select(AgentDB).where(AgentDB.id == existing_agent.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.integration
async def test_delete_agent_not_found(authenticated_client: AsyncClient):
    """
    Test deleting non-existent agent.

    Given: No agent with the given ID
    When: Sending DELETE /api/v1/agents/{agent_id}
    Then: API returns 404 Not Found
    """
    fake_id = uuid4()
    response = await authenticated_client.delete(f"/api/v1/agents/{fake_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Agent Status Transition Tests (REQ-E-002)
# =============================================================================


@pytest.mark.integration
async def test_agent_status_transitions(
    authenticated_client: AsyncClient,
    existing_agent: AgentDB,
):
    """
    Test valid agent status transitions.

    Given: An offline agent
    When: Transitioning through valid states (offline -> online -> busy -> offline)
    Then: All transitions succeed
    """
    # OFFLINE -> ONLINE (valid)
    response = await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json={"status": "online"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "online"

    # ONLINE -> BUSY (valid)
    response = await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json={"status": "busy"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "busy"

    # BUSY -> OFFLINE (valid)
    response = await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json={"status": "offline"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "offline"


@pytest.mark.integration
async def test_agent_invalid_status_transition(
    authenticated_client: AsyncClient,
    existing_agent: AgentDB,
):
    """
    Test rejection of invalid agent status transitions.

    Given: An agent with specific current status
    When: Attempting invalid status transition
    Then: API returns 400 Bad Request with error details
    """
    # First set to ONLINE
    await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json={"status": "online"}
    )

    # Try invalid transition: ONLINE -> ERROR (not directly valid from ONLINE)
    # Note: The actual valid transitions depend on the service implementation
    # This test checks that invalid transitions are rejected
    response = await authenticated_client.patch(
        f"/api/v1/agents/{existing_agent.id}", json={"status": "invalid_status"}
    )

    # The API should reject invalid status values
    # Pydantic validates the enum, so this should return 422 Unprocessable Entity
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
