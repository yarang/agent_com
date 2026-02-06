"""
End-to-end tests for Task persistence.

Tests complete task lifecycle to ensure data persists across
page refreshes (simulated by new database sessions).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent import AgentDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.task import TaskDB
from agent_comm_core.models.auth import User
from agent_comm_core.models.common import TaskStatus

# =============================================================================
# E2E Scenario: Task Persistence Across Page Refresh (REQ-E-004, REQ-N-003)
# =============================================================================


@pytest.mark.e2e
async def test_task_persistence_scenario(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Full lifecycle test for task persistence.

    Given: Empty database
    When:
        1. Create project with agents
        2. Create task via API
        3. Assign task to agent
        4. Update task status through lifecycle
        5. Simulate page refresh (new DB session)
    Then:
        1. Task data persists correctly
        2. Status history is maintained
        3. All relationships are preserved
    """
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup: Create user, project, and agent
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="E2E Task Project",
        owner_id=user_id,
    )
    clean_db.add(project)

    agent = AgentDB(
        id=uuid4(),
        project_id=project.id,
        name="Task Agent",
        status="online",
        is_active=True,
        capabilities=["task_handler"],
    )
    clean_db.add(agent)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        email="task@example.com",
        name="Task User",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # ============================================================================
    # Step 1: Create task via API
    # ============================================================================

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        task_data = {
            "project_id": str(project.id),
            "title": "Persistent Task",
            "description": "Task that should persist across refresh",
            "priority": "high",
        }

        response = await client.post("/api/v1/tasks", json=task_data)
        assert response.status_code == 201

        created_task = response.json()
        task_id = UUID(created_task["id"])

        # Verify initial state
        assert created_task["title"] == "Persistent Task"
        assert created_task["description"] == "Task that should persist across refresh"
        assert created_task["priority"] == "high"
        assert created_task["status"] == TaskStatus.PENDING.value
        assert created_task["assigned_to"] is None

    # ============================================================================
    # Step 2: Assign task to agent
    # ============================================================================

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assign_data = {
            "assigned_to": str(agent.id),
            "assigned_to_type": "agent",
        }

        response = await client.post(f"/api/v1/tasks/{task_id}/assign", json=assign_data)
        assert response.status_code == 200

        assigned_task = response.json()
        assert assigned_task["assigned_to"] == str(agent.id)
        assert assigned_task["assigned_to_type"] == "agent"

    # ============================================================================
    # Step 3: Update task status through lifecycle
    # ============================================================================

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # PENDING -> IN_PROGRESS
        response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
        assert response.status_code == 200
        in_progress_task = response.json()
        assert in_progress_task["status"] == "in_progress"
        assert in_progress_task["started_at"] is not None

        # IN_PROGRESS -> REVIEW
        response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "review"})
        assert response.status_code == 200
        review_task = response.json()
        assert review_task["status"] == "review"

        # REVIEW -> COMPLETED with result
        response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={
                "status": "completed",
                "result": {"output": "Task completed successfully", "metrics": {"time": 42}},
            },
        )
        assert response.status_code == 200
        completed_task = response.json()
        assert completed_task["status"] == "completed"
        assert completed_task["completed_at"] is not None
        assert completed_task["result"]["output"] == "Task completed successfully"

    # ============================================================================
    # Step 4: Simulate page refresh (new DB session)
    # ============================================================================

    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        # Query task from new session
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task_id))
        refreshed_task = result.scalar_one_or_none()

        # Verify task persists after "refresh"
        assert refreshed_task is not None
        assert refreshed_task.id == task_id
        assert refreshed_task.title == "Persistent Task"
        assert refreshed_task.description == "Task that should persist across refresh"
        assert refreshed_task.priority == "high"
        assert refreshed_task.status == "completed"
        assert refreshed_task.assigned_to == agent.id
        assert refreshed_task.assigned_to_type == "agent"

        # Verify status history (timestamps)
        assert refreshed_task.started_at is not None
        assert refreshed_task.completed_at is not None
        assert refreshed_task.completed_at > refreshed_task.started_at

        # Verify result persists
        assert refreshed_task.result is not None
        assert refreshed_task.result["output"] == "Task completed successfully"
        assert refreshed_task.result["metrics"]["time"] == 42

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_task_dependencies_persistence(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test task dependencies persist correctly.

    Given: Multiple tasks with dependencies
    When: Creating task dependency chains
    Then: Dependencies persist across sessions
    """
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="Dependency Project",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        email="dep@example.com",
        name="Dependency User",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Create task chain: Task1 -> Task2 -> Task3
    task_ids = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create first task (no dependencies)
        response1 = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Task 1 (Foundation)",
            },
        )
        assert response1.status_code == 201
        task1_id = UUID(response1.json()["id"])
        task_ids.append(task1_id)

        # Create second task (depends on Task1)
        response2 = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Task 2 (Depends on Task1)",
                "dependencies": [str(task1_id)],
            },
        )
        assert response2.status_code == 201
        task2_id = UUID(response2.json()["id"])
        task_ids.append(task2_id)

        # Create third task (depends on Task2)
        response3 = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Task 3 (Depends on Task2)",
                "dependencies": [str(task2_id)],
            },
        )
        assert response3.status_code == 201
        task3_id = UUID(response3.json()["id"])
        task_ids.append(task3_id)

    # Verify dependencies persist in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        # Verify Task1 (no dependencies)
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task1_id))
        task1 = result.scalar_one()
        assert task1.dependencies == []

        # Verify Task2 (depends on Task1)
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task2_id))
        task2 = result.scalar_one()
        assert task2.dependencies == [task1_id]

        # Verify Task3 (depends on Task2)
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task3_id))
        task3 = result.scalar_one()
        assert task3.dependencies == [task2_id]

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_task_timestamp_tracking(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test task timestamps are correctly tracked.

    Given: A task moving through statuses
    When: Status changes occur
    Then: Timestamps reflect the correct times
    """
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="Timestamp Project",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        email="time@example.com",
        name="Timestamp User",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    task_id: UUID | None = None
    initial_created_at: datetime | None = None

    # Create task and record timestamps
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Timestamp Test Task",
            },
        )
        assert response.status_code == 201
        task_data = response.json()
        task_id = UUID(task_data["id"])
        initial_created_at = datetime.fromisoformat(task_data["created_at"])

        assert task_data["started_at"] is None
        assert task_data["completed_at"] is None

    # Move to in_progress
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await asyncio.sleep(0.01)  # Small delay to ensure timestamp difference

        response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
        assert response.status_code == 200
        task_data = response.json()
        started_at = datetime.fromisoformat(task_data["started_at"])

        assert started_at > initial_created_at
        assert task_data["completed_at"] is None

    # Move to completed
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await asyncio.sleep(0.01)

        response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "completed"})
        assert response.status_code == 200
        task_data = response.json()
        completed_at = datetime.fromisoformat(task_data["completed_at"])

        assert completed_at > started_at

    # Verify in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task_id))
        task = result.scalar_one()

        assert task.created_at == initial_created_at
        assert task.started_at is not None
        assert task.completed_at is not None
        assert task.completed_at > task.started_at > task.created_at

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_task_reopening_from_completed(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test task can be reopened after completion.

    Given: A completed task
    When: Status is changed back to in_progress
    Then: Task reopens with updated timestamps
    """
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="Reopen Project",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        email="reopen@example.com",
        name="Reopen User",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    task_id: UUID | None = None

    # Create and complete task
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Reopenable Task",
            },
        )
        assert response.status_code == 201
        task_id = UUID(response.json()["id"])

        # Complete the task
        response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "completed"})
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    # Reopen the task
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    # Verify in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task_id))
        task = result.scalar_one()
        assert task.status == "in_progress"

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_task_due_date_overdue_detection(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test task due date and overdue detection.

    Given: Tasks with different due dates
    When: Time passes and due dates are reached
    Then: Overdue status is correctly detected
    """
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="Due Date Project",
        owner_id=user_id,
    )
    clean_db.add(project)
    await clean_db.commit()

    test_user = User(
        id=user_id,
        email="due@example.com",
        name="Due Date User",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    now = datetime.now(UTC)
    overdue_task_id: UUID | None = None
    future_task_id: UUID | None = None

    # Create tasks with different due dates
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Overdue task (due in the past)
        response1 = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Overdue Task",
                "due_date": (now - timedelta(days=1)).isoformat(),
            },
        )
        assert response1.status_code == 201
        overdue_task_id = UUID(response1.json()["id"])

        # Future task (due in the future)
        response2 = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Future Task",
                "due_date": (now + timedelta(days=7)).isoformat(),
            },
        )
        assert response2.status_code == 201
        future_task_id = UUID(response2.json()["id"])

    # Verify in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        # Check overdue task
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == overdue_task_id))
        overdue_task = result.scalar_one()
        assert overdue_task.due_date < now
        assert overdue_task.is_overdue is True

        # Check future task
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == future_task_id))
        future_task = result.scalar_one()
        assert future_task.due_date > now
        assert future_task.is_overdue is False

    app.dependency_overrides.clear()


@pytest.mark.e2e
async def test_task_assignment_and_reassignment(
    clean_db: AsyncSession,
    test_engine,
):
    """
    Test task assignment and reassignment persistence.

    Given: A task and multiple agents
    When: Assigning, reassigning, and unassigning
    Then: Assignment changes persist correctly
    """
    from httpx import ASGITransport

    from communication_server.main import app
    from communication_server.security.dependencies import get_current_user

    # Setup
    user_id = uuid4()
    project = ProjectDB(
        id=uuid4(),
        name="Assignment Project",
        owner_id=user_id,
    )
    clean_db.add(project)

    agent1 = AgentDB(
        id=uuid4(),
        project_id=project.id,
        name="Agent 1",
        status="online",
        is_active=True,
        capabilities=[],
    )
    agent2 = AgentDB(
        id=uuid4(),
        project_id=project.id,
        name="Agent 2",
        status="online",
        is_active=True,
        capabilities=[],
    )
    clean_db.add_all([agent1, agent2])
    await clean_db.commit()

    test_user = User(
        id=user_id,
        email="assign@example.com",
        name="Assignment User",
        is_superuser=False,
    )

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    task_id: UUID | None = None

    # Create task
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "project_id": str(project.id),
                "title": "Assignment Test Task",
            },
        )
        assert response.status_code == 201
        task_id = UUID(response.json()["id"])
        assert response.json()["assigned_to"] is None

    # Assign to Agent 1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/tasks/{task_id}/assign",
            json={
                "assigned_to": str(agent1.id),
                "assigned_to_type": "agent",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == str(agent1.id)

    # Reassign to Agent 2
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/tasks/{task_id}/assign",
            json={
                "assigned_to": str(agent2.id),
                "assigned_to_type": "agent",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == str(agent2.id)

    # Unassign
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"assigned_to": None, "assigned_to_type": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] is None

    # Verify final state in new session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session_maker() as new_session:
        result = await new_session.execute(select(TaskDB).where(TaskDB.id == task_id))
        task = result.scalar_one()
        assert task.assigned_to is None
        assert task.assigned_to_type is None

    app.dependency_overrides.clear()


# Import asyncio for sleep in timestamp test
import asyncio
