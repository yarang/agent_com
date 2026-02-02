"""
Characterization tests for Project API behavior.

These tests capture the CURRENT BEHAVIOR of the project API
to ensure no regressions occur during refactoring to database persistence.

IMPORTANT: These tests document WHAT the system does, not what it SHOULD do.
If behavior needs to change, update these tests to reflect new expectations.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.user import UserDB, UserRole
from agent_comm_core.models.auth import TokenData

# =============================================================================
# Characterization Test Helpers
# =============================================================================


class ProjectAPITestContext:
    """Context for project API characterization tests."""

    def __init__(self, client: AsyncClient, db_session: AsyncSession, test_user: UserDB):
        self.client = client
        self.db_session = db_session
        self.test_user = test_user
        self.auth_headers = {"Authorization": f"Bearer {self._get_test_token()}"}

    def _get_test_token(self) -> str:
        """Generate a test JWT token for the test user."""
        from communication_server.security.auth import create_access_token

        return create_access_token(
            TokenData(sub=str(self.test_user.id), username=self.test_user.username)
        )


async def create_test_user(db_session: AsyncSession, username: str = "testuser") -> UserDB:
    """Create a test user in the database."""
    user = UserDB(
        username=username,
        email=f"{username}@example.com",
        password_hash="test_hash",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# =============================================================================
# Characterization Tests: Project CRUD
# =============================================================================


class TestCharacterizeProjectCreate:
    """Characterize project creation behavior."""

    @pytest.mark.asyncio
    async def test_characterize_create_project_success(self, clean_db: AsyncSession):
        """Characterize: Creating a project returns project info with API keys."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Execute
            request_data = {
                "project_id": "test-project",
                "name": "Test Project",
                "description": "A test project",
                "tags": ["test", "characterization"],
            }
            response = await ctx.client.post(
                "/api/v1/projects/",
                json=request_data,
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 201
            data = response.json()

            # Current behavior: returns project_id, name, description, tags
            assert "project_id" in data
            assert data["project_id"] == "test-project"
            assert "name" in data
            assert data["name"] == "Test Project"
            assert "description" in data
            assert "api_keys" in data  # API keys returned on creation
            assert isinstance(data["api_keys"], list)
            assert "created_at" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_characterize_create_project_duplicate(self, clean_db: AsyncSession):
        """Characterize: Creating duplicate project returns 400."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create first project
            request_data = {
                "project_id": "duplicate-test",
                "name": "First Project",
            }
            await ctx.client.post(
                "/api/v1/projects/",
                json=request_data,
                headers=ctx.auth_headers,
            )

            # Try to create duplicate
            response = await ctx.client.post(
                "/api/v1/projects/",
                json=request_data,
                headers=ctx.auth_headers,
            )

            # Characterize: Currently returns 400 for duplicate
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


class TestCharacterizeProjectList:
    """Characterize project listing behavior."""

    @pytest.mark.asyncio
    async def test_characterize_list_projects_empty(self, clean_db: AsyncSession):
        """Characterize: Listing projects with no projects returns empty list."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            response = await ctx.client.get(
                "/api/v1/projects/",
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 200
            data = response.json()
            assert "projects" in data
            assert isinstance(data["projects"], list)
            # Current behavior: returns special "_none" entry for agents without projects

    @pytest.mark.asyncio
    async def test_characterize_list_projects_with_data(self, clean_db: AsyncSession):
        """Characterize: Listing projects returns agent count information."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create a project
            await ctx.client.post(
                "/api/v1/projects/",
                json={"project_id": "list-test", "name": "List Test"},
                headers=ctx.auth_headers,
            )

            response = await ctx.client.get(
                "/api/v1/projects/",
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 200
            data = response.json()
            projects = data["projects"]

            # Current behavior: each project has project_id, name, agent_count, active_count, is_online
            for project in projects:
                if project["project_id"] is not None:  # Skip _none entry
                    assert "project_id" in project
                    assert "name" in project
                    assert "agent_count" in project
                    assert "active_count" in project
                    assert "is_online" in project


class TestCharacterizeProjectGet:
    """Characterize project retrieval behavior."""

    @pytest.mark.asyncio
    async def test_characterize_get_project_success(self, clean_db: AsyncSession):
        """Characterize: Getting existing project returns full project info."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create project first
            await ctx.client.post(
                "/api/v1/projects/",
                json={"project_id": "get-test", "name": "Get Test"},
                headers=ctx.auth_headers,
            )

            response = await ctx.client.get(
                "/api/v1/projects/get-test",
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 200
            data = response.json()
            assert "project_id" in data
            assert "name" in data
            assert "description" in data
            assert "tags" in data
            assert "status" in data
            assert "created_at" in data
            assert "last_modified" in data
            assert "statistics" in data

    @pytest.mark.asyncio
    async def test_characterize_get_project_not_found(self, clean_db: AsyncSession):
        """Characterize: Getting non-existent project returns 404."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            response = await ctx.client.get(
                "/api/v1/projects/non-existent",
                headers=ctx.auth_headers,
            )

            # Characterize: returns 404
            assert response.status_code == 404


class TestCharacterizeProjectUpdate:
    """Characterize project update behavior."""

    @pytest.mark.asyncio
    async def test_characterize_update_project_success(self, clean_db: AsyncSession):
        """Characterize: Updating project updates name, description, tags."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create project
            await ctx.client.post(
                "/api/v1/projects/",
                json={"project_id": "update-test", "name": "Original Name"},
                headers=ctx.auth_headers,
            )

            # Update project
            update_data = {
                "name": "Updated Name",
                "description": "Updated description",
                "tags": ["updated"],
            }
            response = await ctx.client.put(
                "/api/v1/projects/update-test",
                json=update_data,
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"
            assert data["description"] == "Updated description"
            assert data["tags"] == ["updated"]


class TestCharacterizeProjectDelete:
    """Characterize project deletion behavior."""

    @pytest.mark.asyncio
    async def test_characterize_delete_project_success(self, clean_db: AsyncSession):
        """Characterize: Deleting project returns confirmation message."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create project
            await ctx.client.post(
                "/api/v1/projects/",
                json={"project_id": "delete-test", "name": "Delete Test"},
                headers=ctx.auth_headers,
            )

            # Delete project
            response = await ctx.client.delete(
                "/api/v1/projects/delete-test",
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "project_id" in data
            assert "deleted successfully" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_characterize_delete_project_not_found(self, clean_db: AsyncSession):
        """Characterize: Deleting non-existent project returns 404."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            response = await ctx.client.delete(
                "/api/v1/projects/non-existent",
                headers=ctx.auth_headers,
            )

            # Characterize: returns 404
            assert response.status_code == 404


class TestCharacterizeProjectMessages:
    """Characterize project messaging behavior."""

    @pytest.mark.asyncio
    async def test_characterize_send_project_message(self, clean_db: AsyncSession):
        """Characterize: Sending message creates message with auto-generated ID."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create project
            await ctx.client.post(
                "/api/v1/projects/",
                json={"project_id": "message-test", "name": "Message Test"},
                headers=ctx.auth_headers,
            )

            # Send message
            message_data = {
                "from_agent": "test-agent",
                "content": "Test message",
                "message_type": "statement",
            }
            response = await ctx.client.post(
                "/api/v1/projects/message-test/messages",
                json=message_data,
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 201
            data = response.json()
            assert "message_id" in data
            assert "project_id" in data
            assert "from_agent" in data
            assert "content" in data
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_characterize_get_project_messages(self, clean_db: AsyncSession):
        """Characterize: Getting messages returns paginated list."""
        from communication_server.main import app

        # Setup
        user = await create_test_user(clean_db)
        await clean_db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ctx = ProjectAPITestContext(client, clean_db, user)

            # Create project
            await ctx.client.post(
                "/api/v1/projects/",
                json={"project_id": "get-messages-test", "name": "Get Messages Test"},
                headers=ctx.auth_headers,
            )

            # Send a message first
            await ctx.client.post(
                "/api/v1/projects/get-messages-test/messages",
                json={
                    "from_agent": "test-agent",
                    "content": "Test message",
                    "message_type": "statement",
                },
                headers=ctx.auth_headers,
            )

            # Get messages
            response = await ctx.client.get(
                "/api/v1/projects/get-messages-test/messages",
                headers=ctx.auth_headers,
            )

            # Characterize current behavior
            assert response.status_code == 200
            data = response.json()
            assert "project_id" in data
            assert "messages" in data
            assert "pagination" in data
            assert isinstance(data["messages"], list)


# =============================================================================
# Test fixtures
# =============================================================================


@pytest_asyncio.fixture
async def clean_db(clean_db: AsyncSession) -> AsyncSession:
    """Clean database before project tests."""
    # Delete existing project data
    await clean_db.execute(delete(ProjectDB))
    await clean_db.commit()
    return clean_db
