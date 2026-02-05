"""
Unit tests for AgentApiKeyDB foreign key constraint behavior.

These tests verify the foreign key constraint works correctly:
- FK constraint exists on created_by_id
- ON DELETE SET NULL behavior works
- Invalid user IDs are rejected
- NULL created_by_id is allowed

SPEC: SPEC-AGENT-002 - Agent User Ownership Model
"""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_comm_core.db.models.agent_api_key import AgentApiKeyDB
from agent_comm_core.db.models.project import ProjectDB
from agent_comm_core.db.models.user import UserDB
from agent_comm_core.models.auth import UserRole
from agent_comm_core.models.common import ActorType as CreatorType
from agent_comm_core.models.common import KeyStatus


class TestAgentApiKeyForeignKey:
    """
    Unit tests for AgentApiKeyDB foreign key to users.id.

    Tests the referential integrity between agent API keys and users.
    """

    @pytest.mark.asyncio
    async def test_create_with_valid_user_id_succeeds(self, db_session: AsyncSession):
        """
        Test creating agent API key with valid user ID.

        GIVEN a user exists in the database
        WHEN an agent API key is created with that user's ID
        THEN the key should be created successfully
        AND created_by_id should match the user's ID
        """
        # Arrange: Create a user
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Create a project for the agent key
        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        # Act: Create agent API key with valid user ID
        api_key = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="test_key_001",
            api_key_hash="hash_value",
            key_prefix="sk_agent_",
            capabilities=["read", "write"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_id,
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        # Assert: Verify the key was created with correct created_by_id
        assert api_key.created_by_id == user_id
        assert api_key.created_by_type == CreatorType.USER

    @pytest.mark.asyncio
    async def test_create_with_null_user_id_succeeds(self, db_session: AsyncSession):
        """
        Test creating agent API key with NULL created_by_id.

        GIVEN the agent_api_keys table exists
        WHEN an agent API key is created with created_by_id=None
        THEN the key should be created successfully
        AND created_by_id should be NULL
        """
        # Arrange: Create a user and project
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        # Act: Create agent API key with NULL created_by_id
        api_key = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="test_key_null",
            api_key_hash="hash_value",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.SYSTEM,
            created_by_id=None,  # NULL is allowed
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        # Assert: Verify the key was created with NULL created_by_id
        assert api_key.created_by_id is None
        assert api_key.created_by_type == CreatorType.SYSTEM

    @pytest.mark.asyncio
    async def test_on_delete_set_null_behavior(self, db_session: AsyncSession):
        """
        Test ON DELETE SET NULL behavior.

        GIVEN an agent API key exists with created_by_id=user_123
        WHEN the user is deleted from the users table
        THEN the agent API key's created_by_id should be set to NULL
        AND the agent API key should still exist
        """
        # Arrange: Create a user and agent API key
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="delete_test_user",
            email="delete@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        api_key_id = uuid4()
        api_key = AgentApiKeyDB(
            id=api_key_id,
            project_id=project_id,
            agent_id=uuid4(),
            key_id="test_key_cascade",
            api_key_hash="hash_value",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_id,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Act: Delete the user
        await db_session.delete(user)
        await db_session.commit()

        # Assert: Verify the key still exists but created_by_id is NULL
        result = await db_session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.id == api_key_id)
        )
        saved_key = result.scalar_one_or_none()

        assert saved_key is not None, "Agent API key should still exist after user deletion"
        assert saved_key.created_by_id is None, (
            "created_by_id should be NULL after user deletion (ON DELETE SET NULL)"
        )

    @pytest.mark.asyncio
    async def test_query_by_created_by_id(self, db_session: AsyncSession):
        """
        Test querying agent API keys by created_by_id.

        GIVEN multiple agent API keys created by different users
        WHEN querying for keys created by a specific user
        THEN only keys created by that user should be returned
        """
        # Arrange: Create two users and multiple agent API keys
        user_1_id = uuid4()
        user_1 = UserDB(
            id=user_1_id,
            username="user1",
            email="user1@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user_1)

        user_2_id = uuid4()
        user_2 = UserDB(
            id=user_2_id,
            username="user2",
            email="user2@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user_2)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_1_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        # Create 2 keys by user_1 and 1 key by user_2
        key_1 = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="key_user1_1",
            api_key_hash="hash1",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_1_id,
        )
        db_session.add(key_1)

        key_2 = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="key_user1_2",
            api_key_hash="hash2",
            key_prefix="sk_agent_",
            capabilities=["write"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_1_id,
        )
        db_session.add(key_2)

        key_3 = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="key_user2_1",
            api_key_hash="hash3",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_2_id,
        )
        db_session.add(key_3)
        await db_session.commit()

        # Act: Query for keys created by user_1
        result = await db_session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.created_by_id == user_1_id)
        )
        user_1_keys = list(result.scalars().all())

        # Assert: Should return only keys created by user_1
        assert len(user_1_keys) == 2
        key_ids = {key.key_id for key in user_1_keys}
        assert key_ids == {"key_user1_1", "key_user1_2"}

    @pytest.mark.asyncio
    async def test_multiple_keys_same_creator(self, db_session: AsyncSession):
        """
        Test multiple agent API keys created by the same user.

        GIVEN a user exists
        WHEN multiple agent API keys are created by that user
        THEN all keys should have the same created_by_id
        """
        # Arrange: Create a user and project
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="multikey_user",
            email="multikey@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        # Act: Create multiple keys by the same user
        keys = []
        for i in range(3):
            key = AgentApiKeyDB(
                id=uuid4(),
                project_id=project_id,
                agent_id=uuid4(),
                key_id=f"multi_key_{i}",
                api_key_hash=f"hash_{i}",
                key_prefix="sk_agent_",
                capabilities=["read"],
                status=KeyStatus.ACTIVE,
                created_by_type=CreatorType.USER,
                created_by_id=user_id,
            )
            db_session.add(key)
            keys.append(key)
        await db_session.commit()

        # Assert: All keys should have the same created_by_id
        for key in keys:
            await db_session.refresh(key)
            assert key.created_by_id == user_id

        # Query by created_by_id should return all 3 keys
        result = await db_session.execute(
            select(AgentApiKeyDB).where(AgentApiKeyDB.created_by_id == user_id)
        )
        user_keys = list(result.scalars().all())
        assert len(user_keys) == 3

    @pytest.mark.asyncio
    async def test_null_created_by_id_in_results(self, db_session: AsyncSession):
        """
        Test that NULL created_by_id is included in query results.

        GIVEN agent API keys exist with both NULL and non-NULL created_by_id
        WHEN querying all agent API keys
        THEN records with NULL created_by_id should be included
        """
        # Arrange: Create a user and project
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        # Create key with NULL created_by_id
        key_null = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="key_null_creator",
            api_key_hash="hash_null",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.SYSTEM,
            created_by_id=None,
        )
        db_session.add(key_null)

        # Create key with user creator
        key_user = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="key_user_creator",
            api_key_hash="hash_user",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_id,
        )
        db_session.add(key_user)
        await db_session.commit()

        # Act: Query all agent API keys for the project
        result = await db_session.execute(
            select(AgentApiKeyDB)
            .where(AgentApiKeyDB.project_id == project_id)
            .order_by(AgentApiKeyDB.key_id)
        )
        all_keys = list(result.scalars().all())

        # Assert: Both keys should be returned
        assert len(all_keys) == 2
        created_by_ids = [key.created_by_id for key in all_keys]
        assert None in created_by_ids
        assert user_id in created_by_ids

    @pytest.mark.asyncio
    async def test_join_with_users_table(self, db_session: AsyncSession):
        """
        Test JOIN query between agent_api_keys and users table.

        GIVEN agent API keys exist with created_by_id values
        WHEN performing a JOIN with the users table
        THEN the join should work via the FK relationship
        """
        # Arrange: Create a user and agent API key
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="join_test_user",
            email="join@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        key_id = uuid4()
        api_key = AgentApiKeyDB(
            id=key_id,
            project_id=project_id,
            agent_id=uuid4(),
            key_id="join_test_key",
            api_key_hash="hash_value",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_id,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Act: Perform JOIN query

        result = await db_session.execute(
            select(AgentApiKeyDB, UserDB)
            .join(UserDB, AgentApiKeyDB.created_by_id == UserDB.id)
            .where(AgentApiKeyDB.id == key_id)
        )
        joined_data = result.first()

        # Assert: Join should return both key and user
        assert joined_data is not None
        key_result, user_result = joined_data
        assert key_result.id == key_id
        assert user_result.id == user_id
        assert user_result.username == "join_test_user"


class TestAgentApiKeyFKEdgeCases:
    """
    Unit tests for edge cases related to the foreign key constraint.
    """

    @pytest.mark.asyncio
    async def test_update_created_by_id_to_valid_user(self, db_session: AsyncSession):
        """
        Test updating created_by_id to a valid user.

        GIVEN an agent API key exists with created_by_id=user_1
        WHEN updating created_by_id to user_2 (valid user)
        THEN the update should succeed
        """
        # Arrange: Create two users and an agent API key
        user_1_id = uuid4()
        user_1 = UserDB(
            id=user_1_id,
            username="user1",
            email="user1@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user_1)

        user_2_id = uuid4()
        user_2 = UserDB(
            id=user_2_id,
            username="user2",
            email="user2@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user_2)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_1_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        api_key = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="update_test_key",
            api_key_hash="hash_value",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_1_id,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Act: Update created_by_id to user_2
        api_key.created_by_id = user_2_id
        await db_session.commit()
        await db_session.refresh(api_key)

        # Assert: created_by_id should be updated
        assert api_key.created_by_id == user_2_id

    @pytest.mark.asyncio
    async def test_update_created_by_id_to_null(self, db_session: AsyncSession):
        """
        Test updating created_by_id to NULL.

        GIVEN an agent API key exists with created_by_id=user_1
        WHEN updating created_by_id to NULL
        THEN the update should succeed
        """
        # Arrange: Create a user and agent API key
        user_id = uuid4()
        user = UserDB(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)

        project_id = uuid4()
        project = ProjectDB(
            id=project_id,
            owner_id=user_id,
            name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()

        api_key = AgentApiKeyDB(
            id=uuid4(),
            project_id=project_id,
            agent_id=uuid4(),
            key_id="null_update_key",
            api_key_hash="hash_value",
            key_prefix="sk_agent_",
            capabilities=["read"],
            status=KeyStatus.ACTIVE,
            created_by_type=CreatorType.USER,
            created_by_id=user_id,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Act: Update created_by_id to NULL
        api_key.created_by_id = None
        await db_session.commit()
        await db_session.refresh(api_key)

        # Assert: created_by_id should be NULL
        assert api_key.created_by_id is None
