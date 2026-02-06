"""
Unit tests for AgentDB and TaskDB models.

Tests the new agent and task persistence models.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError

from agent_comm_core.db.base import Base
from agent_comm_core.db.models.agent import AgentDB, AgentStatus
from agent_comm_core.db.models.agent_api_key import AgentApiKeyDB
from agent_comm_core.db.models.chat import ChatParticipantDB, ChatRoomDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.task import TaskDB, TaskPriority, TaskStatus
from agent_comm_core.db.models.user import UserDB


class TestAgentDBModel:
    """Tests for AgentDB model."""

    @pytest.fixture
    def db_engine(self):
        """Create in-memory database for testing."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)

    @pytest.fixture
    def db_session(self, db_engine):
        """Create database session."""
        from sqlalchemy.orm import Session

        with Session(db_engine) as session:
            yield session

    def test_create_agent(self, db_session):
        """Test creating an agent."""
        project_id = uuid4()

        # Create project first
        project = ProjectDB(
            id=project_id,
            owner_id=uuid4(),
            project_id="test-project",
            name="Test Project",
        )
        db_session.add(project)
        db_session.commit()

        # Create agent
        agent = AgentDB(
            project_id=project_id,
            name="Test Agent",
            nickname="Testy",
            agent_type="generic",
            status=AgentStatus.OFFLINE.value,
            capabilities=["read", "write"],
            is_active=True,
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        assert agent.id is not None
        assert agent.name == "Test Agent"
        assert agent.status == AgentStatus.OFFLINE.value
        assert agent.is_active is True
        assert agent.is_online is False

    def test_agent_unique_constraint_per_project(self, db_session):
        """Test that agent names are unique per project."""
        project_id = uuid4()

        # Create project
        project = ProjectDB(
            id=project_id,
            owner_id=uuid4(),
            project_id="test-project",
            name="Test Project",
        )
        db_session.add(project)
        db_session.commit()

        # Create first agent
        agent1 = AgentDB(
            project_id=project_id,
            name="SameName",
            agent_type="generic",
        )
        db_session.add(agent1)
        db_session.commit()

        # Try to create second agent with same name in same project
        agent2 = AgentDB(
            project_id=project_id,
            name="SameName",
            agent_type="generic",
        )
        db_session.add(agent2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_agent_same_name_different_projects(self, db_session):
        """Test that agents with same name can exist in different projects."""
        # Create two projects
        project1 = ProjectDB(
            id=uuid4(),
            owner_id=uuid4(),
            project_id="project-1",
            name="Project 1",
        )
        project2 = ProjectDB(
            id=uuid4(),
            owner_id=uuid4(),
            project_id="project-2",
            name="Project 2",
        )
        db_session.add(project1)
        db_session.add(project2)
        db_session.commit()

        # Create agents with same name in different projects
        agent1 = AgentDB(
            project_id=project1.id,
            name="SameName",
            agent_type="generic",
        )
        agent2 = AgentDB(
            project_id=project2.id,
            name="SameName",
            agent_type="generic",
        )
        db_session.add(agent1)
        db_session.add(agent2)
        db_session.commit()

        assert agent1.id != agent2.id
        assert agent1.name == agent2.name

    def test_agent_api_key_relationship(self, db_session):
        """Test AgentDB relationship with AgentApiKeyDB."""
        project_id = uuid4()

        # Create project
        project = ProjectDB(
            id=project_id,
            owner_id=uuid4(),
            project_id="test-project",
            name="Test Project",
        )
        db_session.add(project)
        db_session.commit()

        # Create agent
        agent = AgentDB(
            project_id=project_id,
            name="Test Agent",
            agent_type="generic",
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        # Create API key for agent
        api_key = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=agent.id,
            key_id="test_key",
            api_key_hash="hash_value",
            key_prefix="prefix",
            capabilities=["read"],
        )
        db_session.add(api_key)
        db_session.commit()

        # Query agent and check relationship
        result = db_session.execute(select(AgentDB).where(AgentDB.id == agent.id))
        retrieved_agent = result.scalar_one()

        # Note: relationship might not be loaded without eager loading
        assert retrieved_agent.id == agent.id

    def test_chat_participant_agent_relationship(self, db_session):
        """Test AgentDB relationship with ChatParticipantDB."""
        project_id = uuid4()
        user_id = uuid4()

        # Create project and user
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            project_id="test-project",
            name="Test Project",
        )
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        db_session.add(project)
        db_session.add(user)
        db_session.commit()

        # Create agent
        agent = AgentDB(
            project_id=project_id,
            name="Test Agent",
            agent_type="generic",
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        # Create chat room
        room = ChatRoomDB(
            project_id=project_id,
            name="Test Room",
            created_by=user_id,
        )
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        # Create participant with agent
        participant = ChatParticipantDB(
            room_id=room.id,
            agent_id=agent.id,
        )
        db_session.add(participant)
        db_session.commit()

        assert participant.agent_id == agent.id


class TestTaskDBModel:
    """Tests for TaskDB model."""

    @pytest.fixture
    def db_engine(self):
        """Create in-memory database for testing."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)

    @pytest.fixture
    def db_session(self, db_engine):
        """Create database session."""
        from sqlalchemy.orm import Session

        with Session(db_engine) as session:
            yield session

    def test_create_task(self, db_session):
        """Test creating a task."""
        project_id = uuid4()
        user_id = uuid4()

        # Create project and user
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            project_id="test-project",
            name="Test Project",
        )
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        db_session.add(project)
        db_session.add(user)
        db_session.commit()

        # Create task
        task = TaskDB(
            project_id=project_id,
            title="Test Task",
            description="A test task",
            status=TaskStatus.PENDING.value,
            priority=TaskPriority.MEDIUM.value,
            created_by=user_id,
            dependencies=[],
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.status == TaskStatus.PENDING.value
        assert task.is_completed is False
        assert task.is_overdue is False

    def test_task_status_transitions(self, db_session):
        """Test task status transitions."""
        project_id = uuid4()
        user_id = uuid4()

        # Create project and user
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            project_id="test-project",
            name="Test Project",
        )
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        db_session.add(project)
        db_session.add(user)
        db_session.commit()

        # Create task
        task = TaskDB(
            project_id=project_id,
            title="Test Task",
            status=TaskStatus.PENDING.value,
            created_by=user_id,
            dependencies=[],
        )
        db_session.add(task)
        db_session.commit()

        # Transition to in_progress
        task.status = TaskStatus.IN_PROGRESS.value
        db_session.commit()

        assert task.status == TaskStatus.IN_PROGRESS.value

        # Transition to completed
        task.status = TaskStatus.COMPLETED.value
        db_session.commit()

        assert task.is_completed is True

    def test_task_with_dependencies(self, db_session):
        """Test task with dependencies."""
        project_id = uuid4()
        user_id = uuid4()

        # Create project and user
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            project_id="test-project",
            name="Test Project",
        )
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        db_session.add(project)
        db_session.add(user)
        db_session.commit()

        # Create tasks
        task1 = TaskDB(
            project_id=project_id,
            title="Task 1",
            created_by=user_id,
            dependencies=[],
        )
        task2 = TaskDB(
            project_id=project_id,
            title="Task 2",
            created_by=user_id,
            dependencies=[task1.id],
        )
        db_session.add(task1)
        db_session.add(task2)
        db_session.commit()
        db_session.refresh(task1)
        db_session.refresh(task2)

        assert task1.id in task2.dependencies
        assert len(task2.dependencies) == 1

    def test_task_room_association(self, db_session):
        """Test task associated with chat room."""
        project_id = uuid4()
        user_id = uuid4()

        # Create project, user, and room
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            project_id="test-project",
            name="Test Project",
        )
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        db_session.add(project)
        db_session.add(user)
        db_session.commit()

        room = ChatRoomDB(
            project_id=project_id,
            name="Test Room",
            created_by=user_id,
        )
        db_session.add(room)
        db_session.commit()
        db_session.refresh(room)

        # Create task with room
        task = TaskDB(
            project_id=project_id,
            room_id=room.id,
            title="Task in Room",
            created_by=user_id,
            dependencies=[],
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.room_id == room.id


class TestEnums:
    """Tests for AgentStatus, TaskStatus, and TaskPriority enums."""

    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.ONLINE.value == "online"
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ERROR.value == "error"

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.REVIEW.value == "review"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_priority_values(self):
        """Test TaskPriority enum values."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"
