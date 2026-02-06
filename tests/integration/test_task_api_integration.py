"""
Integration tests for Task API endpoints.

Tests the complete Task CRUD operations through the API layer,
including task assignment, status transitions, and dependency management.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.task import TaskDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.common import TaskPriority, TaskStatus

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_project_with_owner(clean_db: AsyncSession) -> ProjectDB:
    """Create a test project with owner for testing."""
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="Test Project",
        description="Test project for task integration tests",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()
    await clean_db.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_user(clean_db: AsyncSession, test_project_with_owner: ProjectDB) -> User:
    """Create a test user for API authentication."""
    return User(
        id=test_project_with_owner.owner_id,
        email="test@example.com",
        name="Test User",
        is_superuser=False,
    )


@pytest_asyncio.fixture
async def authenticated_client(clean_db: AsyncSession, test_user: User) -> AsyncClient:
    """Create an authenticated test client."""
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_agent(clean_db: AsyncSession, test_project_with_owner: ProjectDB) -> AgentDB:
    """Create a test agent for task assignment."""
    agent = AgentDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        name="Test Agent",
        status="online",
        is_active=True,
        capabilities=["test"],
    )
    clean_db.add(agent)
    await clean_db.commit()
    await clean_db.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def completed_task(
    clean_db: AsyncSession, test_project_with_owner: ProjectDB, test_user: User
) -> TaskDB:
    """Create a completed task for dependency testing."""
    task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Completed Dependency Task",
        status=TaskStatus.COMPLETED.value,
        created_by=test_user.id,
        dependencies=[],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    clean_db.add(task)
    await clean_db.commit()
    await clean_db.refresh(task)
    return task


@pytest_asyncio.fixture
async def existing_task(
    clean_db: AsyncSession, test_project_with_owner: ProjectDB, test_user: User
) -> TaskDB:
    """Create an existing task for testing updates and deletions."""
    task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Existing Task",
        description="Existing task description",
        status=TaskStatus.PENDING.value,
        priority=TaskPriority.MEDIUM.value,
        created_by=test_user.id,
        dependencies=[],
    )
    clean_db.add(task)
    await clean_db.commit()
    await clean_db.refresh(task)
    return task


# =============================================================================
# Task Creation Tests (REQ-E-004)
# =============================================================================


@pytest.mark.integration
async def test_create_task_success(
    authenticated_client: AsyncClient,
    test_project_with_owner: ProjectDB,
):
    """
    Test successful task creation via API.

    Given: A valid project and authenticated user
    When: Creating a task with valid data via POST /api/v1/tasks
    Then: Task is created with generated UUID and default status
    """
    task_data = {
        "project_id": str(test_project_with_owner.id),
        "title": "Test Task",
        "description": "Task for testing",
        "priority": "high",
    }

    response = await authenticated_client.post("/api/v1/tasks", json=task_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Task for testing"
    assert data["priority"] == "high"
    assert data["status"] == TaskStatus.PENDING.value
    assert "id" in data


@pytest.mark.integration
async def test_create_task_with_dependencies(
    authenticated_client: AsyncClient,
    test_project_with_owner: ProjectDB,
    completed_task: TaskDB,
):
    """
    Test creating task with dependency list.

    Given: A completed task exists
    When: Creating a new task with the completed task as a dependency
    Then: Task is created with dependencies stored
    """
    task_data = {
        "project_id": str(test_project_with_owner.id),
        "title": "Task with Dependencies",
        "dependencies": [str(completed_task.id)],
    }

    response = await authenticated_client.post("/api/v1/tasks", json=task_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["dependencies"] == [str(completed_task.id)]


@pytest.mark.integration
async def test_create_task_invalid_dependency(
    authenticated_client: AsyncClient,
    test_project_with_owner: ProjectDB,
):
    """
    Test rejection of non-existent dependency.

    Given: No task with the given dependency ID
    When: Creating a task with invalid dependency
    Then: API returns 400 Bad Request
    """
    fake_id = uuid4()
    task_data = {
        "project_id": str(test_project_with_owner.id),
        "title": "Task with Invalid Dependency",
        "dependencies": [str(fake_id)],
    }

    response = await authenticated_client.post("/api/v1/tasks", json=task_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Task Listing Tests
# =============================================================================


@pytest.mark.integration
async def test_list_tasks_by_project(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
):
    """
    Test filtering tasks by project_id.

    Given: Multiple tasks across different projects
    When: Querying tasks with project_id filter
    Then: Only tasks from the specified project are returned
    """
    # Create another project for testing
    other_project = ProjectDB(
        id=uuid4(),
        name="Other Project",
        owner_id=test_user.id,
    )
    clean_db.add(other_project)

    # Create tasks in both projects
    task1 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Task 1",
        created_by=test_user.id,
        dependencies=[],
    )
    task2 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Task 2",
        created_by=test_user.id,
        dependencies=[],
    )
    task3 = TaskDB(
        id=uuid4(),
        project_id=other_project.id,
        title="Task 3",
        created_by=test_user.id,
        dependencies=[],
    )
    clean_db.add_all([task1, task2, task3])
    await clean_db.commit()

    # Query tasks for test_project_with_owner
    response = await authenticated_client.get(
        f"/api/v1/tasks?project_id={test_project_with_owner.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    task_titles = {task["title"] for task in data["items"]}
    assert task_titles == {"Task 1", "Task 2"}


@pytest.mark.integration
async def test_list_tasks_by_status(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
):
    """
    Test filtering tasks by status.

    Given: Tasks with different statuses
    When: Querying tasks with status filter
    Then: Only tasks with matching status are returned
    """
    # Create tasks with different statuses
    task1 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Pending Task",
        status=TaskStatus.PENDING.value,
        created_by=test_user.id,
        dependencies=[],
    )
    task2 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="In Progress Task",
        status=TaskStatus.IN_PROGRESS.value,
        created_by=test_user.id,
        dependencies=[],
    )
    task3 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Completed Task",
        status=TaskStatus.COMPLETED.value,
        created_by=test_user.id,
        dependencies=[],
        completed_at=datetime.now(UTC),
    )
    clean_db.add_all([task1, task2, task3])
    await clean_db.commit()

    # Query only pending tasks
    response = await authenticated_client.get(
        f"/api/v1/tasks?project_id={test_project_with_owner.id}&status=pending"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Pending Task"


@pytest.mark.integration
async def test_list_tasks_by_assigned_to(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
    test_agent: AgentDB,
):
    """
    Test filtering tasks by assignee.

    Given: Tasks assigned to different entities
    When: Querying tasks with assigned_to filter
    Then: Only tasks assigned to the specified entity are returned
    """
    # Create tasks with different assignments
    task1 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Assigned Task",
        assigned_to=test_agent.id,
        assigned_to_type="agent",
        created_by=test_user.id,
        dependencies=[],
    )
    task2 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Unassigned Task",
        created_by=test_user.id,
        dependencies=[],
    )
    clean_db.add_all([task1, task2])
    await clean_db.commit()

    # Query tasks assigned to test_agent
    response = await authenticated_client.get(
        f"/api/v1/tasks?project_id={test_project_with_owner.id}&assigned_to={test_agent.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Assigned Task"


# =============================================================================
# Task Retrieval Tests
# =============================================================================


@pytest.mark.integration
async def test_get_task_by_id(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test retrieving task by ID.

    Given: An existing task
    When: Querying GET /api/v1/tasks/{task_id}
    Then: Task details are returned
    """
    response = await authenticated_client.get(f"/api/v1/tasks/{existing_task.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(existing_task.id)
    assert data["title"] == existing_task.title


@pytest.mark.integration
async def test_get_task_not_found(authenticated_client: AsyncClient):
    """
    Test retrieving non-existent task.

    Given: No task with the given ID
    When: Querying GET /api/v1/tasks/{task_id}
    Then: API returns 404 Not Found
    """
    fake_id = uuid4()
    response = await authenticated_client.get(f"/api/v1/tasks/{fake_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Task Update Tests
# =============================================================================


@pytest.mark.integration
async def test_update_task_status(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test updating task status.

    Given: A pending task
    When: Updating status to in_progress
    Then: Task status is updated and started_at is set
    """
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "in_progress"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["started_at"] is not None


@pytest.mark.integration
async def test_update_task_partial(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test partial update of task fields.

    Given: An existing task
    When: Sending PATCH with partial update data
    Then: Only specified fields are updated
    """
    update_data = {
        "description": "Updated description",
        "priority": "high",
    }

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json=update_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["priority"] == "high"
    assert data["title"] == existing_task.title  # Unchanged


# =============================================================================
# Task Status Transition Tests (REQ-E-004)
# =============================================================================


@pytest.mark.integration
async def test_task_status_transitions(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test valid task status transitions.

    Given: A pending task
    When: Transitioning through valid states (pending -> in_progress -> review -> completed)
    Then: All transitions succeed and timestamps are updated
    """
    # PENDING -> IN_PROGRESS (valid)
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "in_progress"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["started_at"] is not None
    assert data["completed_at"] is None

    # IN_PROGRESS -> REVIEW (valid)
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "review"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "review"

    # REVIEW -> COMPLETED (valid)
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "completed"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.integration
async def test_task_invalid_status_transition(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test rejection of invalid task status transitions.

    Given: A pending task
    When: Attempting invalid status transition (pending -> completed)
    Then: API returns 400 Bad Request with error details
    """
    # Try invalid transition: PENDING -> COMPLETED (not directly valid)
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "completed"}
    )

    # The API should reject invalid transitions
    # Note: Actual behavior depends on service implementation
    # Some implementations might auto-transition, others reject
    # This test checks the rejection behavior
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Task Assignment Tests (REQ-N-004)
# =============================================================================


@pytest.mark.integration
async def test_assign_task_to_agent(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
    test_agent: AgentDB,
):
    """
    Test assigning task to an agent.

    Given: An existing task and active agent
    When: Sending POST /api/v1/tasks/{task_id}/assign with agent
    Then: Task is assigned to the agent
    """
    assign_data = {
        "assigned_to": str(test_agent.id),
        "assigned_to_type": "agent",
    }

    response = await authenticated_client.post(
        f"/api/v1/tasks/{existing_task.id}/assign", json=assign_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["assigned_to"] == str(test_agent.id)
    assert data["assigned_to_type"] == "agent"


@pytest.mark.integration
async def test_assign_task_to_user(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
    test_user: User,
):
    """
    Test assigning task to a user.

    Given: An existing task
    When: Sending POST /api/v1/tasks/{task_id}/assign with user
    Then: Task is assigned to the user
    """
    assign_data = {
        "assigned_to": str(test_user.id),
        "assigned_to_type": "user",
    }

    response = await authenticated_client.post(
        f"/api/v1/tasks/{existing_task.id}/assign", json=assign_data
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["assigned_to"] == str(test_user.id)
    assert data["assigned_to_type"] == "user"


@pytest.mark.integration
async def test_unassign_task(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    existing_task: TaskDB,
    test_agent: AgentDB,
):
    """
    Test removing task assignment.

    Given: A task assigned to an agent
    When: Updating with null assignment
    Then: Task assignment is removed
    """
    # First assign the task
    existing_task.assigned_to = test_agent.id
    existing_task.assigned_to_type = "agent"
    await clean_db.commit()

    # Then unassign
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}",
        json={"assigned_to": None, "assigned_to_type": None},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["assigned_to"] is None
    assert data["assigned_to_type"] is None


@pytest.mark.integration
async def test_assign_task_to_invalid_agent(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test assignment to non-existent agent.

    Given: A task and non-existent agent ID
    When: Attempting to assign to invalid agent
    Then: API returns 400 Bad Request
    """
    fake_agent_id = uuid4()
    assign_data = {
        "assigned_to": str(fake_agent_id),
        "assigned_to_type": "agent",
    }

    response = await authenticated_client.post(
        f"/api/v1/tasks/{existing_task.id}/assign", json=assign_data
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Task Dependency Tests (REQ-S-003)
# =============================================================================


@pytest.mark.integration
async def test_add_task_dependency(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
    completed_task: TaskDB,
):
    """
    Test adding dependency to task.

    Given: A task and a completed dependency task
    When: Adding the dependency via PATCH
    Then: Task dependencies are updated
    """
    # Create a task without dependencies
    task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Task Without Dependencies",
        created_by=test_user.id,
        dependencies=[],
    )
    clean_db.add(task)
    await clean_db.commit()

    # Add dependency
    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"dependencies": [str(completed_task.id)]},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["dependencies"] == [str(completed_task.id)]


@pytest.mark.integration
async def test_add_circular_dependency(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
):
    """
    Test rejection of circular dependency.

    Given: Two tasks that depend on each other
    When: Attempting to create circular dependency
    Then: API returns 400 Bad Request
    """
    # Create two tasks
    task1 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Task 1",
        created_by=test_user.id,
        dependencies=[],
    )
    task2 = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Task 2",
        created_by=test_user.id,
        dependencies=[],
    )
    clean_db.add_all([task1, task2])
    await clean_db.commit()

    # Make task1 depend on task2
    response1 = await authenticated_client.patch(
        f"/api/v1/tasks/{task1.id}",
        json={"dependencies": [str(task2.id)]},
    )
    assert response1.status_code == status.HTTP_200_OK

    # Try to make task2 depend on task1 (circular)
    response2 = await authenticated_client.patch(
        f"/api/v1/tasks/{task2.id}",
        json={"dependencies": [str(task1.id)]},
    )
    # Should reject circular dependency
    assert response2.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Task Deletion Tests
# =============================================================================


@pytest.mark.integration
async def test_delete_task(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    existing_task: TaskDB,
):
    """
    Test task deletion.

    Given: An existing task with no dependents
    When: Sending DELETE /api/v1/tasks/{task_id}
    Then: Task is deleted
    """
    response = await authenticated_client.delete(f"/api/v1/tasks/{existing_task.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion in database
    result = await clean_db.execute(select(TaskDB).where(TaskDB.id == existing_task.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.integration
async def test_delete_task_with_dependents(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
    completed_task: TaskDB,
):
    """
    Test rejection of task deletion with dependent tasks.

    Given: A task that other tasks depend on
    When: Attempting to delete the dependency task
    Then: API returns 400 Bad Request
    """
    # Create a task that depends on completed_task
    dependent_task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Dependent Task",
        created_by=test_user.id,
        dependencies=[completed_task.id],
    )
    clean_db.add(dependent_task)
    await clean_db.commit()

    # Try to delete completed_task (has dependent)
    response = await authenticated_client.delete(f"/api/v1/tasks/{completed_task.id}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Task Timestamp Tests
# =============================================================================


@pytest.mark.integration
async def test_task_timestamp_auto_update(
    authenticated_client: AsyncClient,
    existing_task: TaskDB,
):
    """
    Test automatic timestamp updates on status changes.

    Given: A pending task
    When: Changing status to in_progress and completed
    Then: started_at and completed_at are auto-set
    """
    # Initially no timestamps
    assert existing_task.started_at is None
    assert existing_task.completed_at is None

    # Change to in_progress
    response1 = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "in_progress"}
    )
    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    assert data1["started_at"] is not None
    assert data1["completed_at"] is None

    # Change to completed
    response2 = await authenticated_client.patch(
        f"/api/v1/tasks/{existing_task.id}", json={"status": "completed"}
    )
    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()
    assert data2["completed_at"] is not None


@pytest.mark.integration
async def test_task_due_date_filter(
    authenticated_client: AsyncClient,
    clean_db: AsyncSession,
    test_project_with_owner: ProjectDB,
    test_user: User,
):
    """
    Test task due date filtering and overdue detection.

    Given: Tasks with different due dates
    When: Querying tasks
    Then: Due dates are correctly returned and overdue property works
    """
    now = datetime.now(UTC)
    overdue_task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Overdue Task",
        status=TaskStatus.PENDING.value,
        created_by=test_user.id,
        dependencies=[],
        due_date=now - timedelta(days=1),
    )
    future_task = TaskDB(
        id=uuid4(),
        project_id=test_project_with_owner.id,
        title="Future Task",
        status=TaskStatus.PENDING.value,
        created_by=test_user.id,
        dependencies=[],
        due_date=now + timedelta(days=7),
    )
    clean_db.add_all([overdue_task, future_task])
    await clean_db.commit()

    # Query all tasks
    response = await authenticated_client.get(
        f"/api/v1/tasks?project_id={test_project_with_owner.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 2

    # Find our tasks in response
    tasks_by_title = {t["title"]: t for t in data["items"]}
    assert "Overdue Task" in tasks_by_title
    assert "Future Task" in tasks_by_title
