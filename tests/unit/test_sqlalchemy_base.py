"""
Unit tests for SQLAlchemy repository base class.

Tests for the generic SQLAlchemyRepositoryBase that provides
common CRUD operations for all repositories.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from agent_comm_core.db.base import Base
from agent_comm_core.models.common import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase

# ============================================================================
# Test Models
# ============================================================================


class TestModel(Base):
    """Simple test model for repository testing."""

    __tablename__ = "test_models"

    # id, created_at, updated_at inherited from Base
    name: str
    value: int
    status: str

    # Using mapped_column for explicit definition
    from sqlalchemy import Integer, String

    id = Base.id  # type: ignore[attr-defined]
    created_at = Base.created_at  # type: ignore[attr-defined]
    updated_at = Base.updated_at  # type: ignore[attr-defined]

    from sqlalchemy.orm import Mapped, mapped_column

    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="active")


class TestModelWithoutStatus(Base):
    """Test model without status field for soft delete testing."""

    __tablename__ = "test_models_no_status"

    from sqlalchemy import Integer, String
    from sqlalchemy.orm import Mapped, mapped_column

    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[int] = mapped_column(Integer)


# ============================================================================
# Test Repository
# ============================================================================


class TestRepository(SQLAlchemyRepositoryBase[TestModel]):
    """Test repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TestModel)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def async_engine():
    """Create an async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """Create a database session for testing."""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


@pytest.fixture
def test_repository(db_session):
    """Create a test repository instance."""
    return TestRepository(db_session)


@pytest.fixture
async def sample_models(db_session):
    """Create sample models for testing."""
    models = []
    for i in range(5):
        model = TestModel(name=f"test_{i}", value=i * 10, status="active")
        db_session.add(model)
        models.append(model)
    await db_session.flush()
    return models


# ============================================================================
# CRUD Operation Tests
# ============================================================================


class TestCRUDOperations:
    """Tests for basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_entity(self, test_repository, db_session):
        """Test creating a new entity."""
        model = await test_repository.create(name="test_name", value=100, status="active")
        await db_session.flush()

        assert model.id is not None
        assert model.name == "test_name"
        assert model.value == 100
        assert model.status == "active"
        assert model.created_at is not None
        assert model.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_repository, sample_models):
        """Test retrieving an entity by ID."""
        model = sample_models[0]
        result = await test_repository.get_by_id(model.id)

        assert result is not None
        assert result.id == model.id
        assert result.name == model.name

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, test_repository):
        """Test retrieving non-existent entity returns None."""
        result = await test_repository.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_ids(self, test_repository, sample_models):
        """Test retrieving multiple entities by IDs."""
        ids = [m.id for m in sample_models[:3]]
        results = await test_repository.get_by_ids(ids)

        assert len(results) == 3
        assert all(r.id in ids for r in results)

    @pytest.mark.asyncio
    async def test_get_by_ids_empty_list(self, test_repository):
        """Test retrieving with empty ID list returns empty list."""
        results = await test_repository.get_by_ids([])
        assert results == []

    @pytest.mark.asyncio
    async def test_exists(self, test_repository, sample_models):
        """Test checking if entity exists."""
        model = sample_models[0]
        assert await test_repository.exists(model.id) is True
        assert await test_repository.exists(uuid4()) is False

    @pytest.mark.asyncio
    async def test_count(self, test_repository, sample_models):
        """Test counting entities."""
        count = await test_repository.count()
        assert count == len(sample_models)

    @pytest.mark.asyncio
    async def test_count_with_filters(self, test_repository, sample_models):
        """Test counting entities with filters."""
        count = await test_repository.count(filters={"status": "active"})
        assert count == len(sample_models)

    @pytest.mark.asyncio
    async def test_update(self, test_repository, sample_models, db_session):
        """Test updating an entity."""
        model = sample_models[0]
        updated = await test_repository.update(model.id, name="updated_name", value=999)

        assert updated is not None
        assert updated.name == "updated_name"
        assert updated.value == 999

    @pytest.mark.asyncio
    async def test_update_not_found(self, test_repository):
        """Test updating non-existent entity returns None."""
        result = await test_repository.update(uuid4(), name="test")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, test_repository, sample_models, db_session):
        """Test deleting an entity."""
        model = sample_models[0]
        deleted = await test_repository.delete(model.id)

        assert deleted is True
        result = await test_repository.get_by_id(model.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, test_repository):
        """Test deleting non-existent entity returns False."""
        deleted = await test_repository.delete(uuid4())
        assert deleted is False


# ============================================================================
# List Operation Tests
# ============================================================================


class TestListOperations:
    """Tests for list and pagination operations."""

    @pytest.mark.asyncio
    async def test_list_all_default(self, test_repository, sample_models):
        """Test listing all entities with default pagination."""
        result = await test_repository.list_all()
        entities = list(result.all())

        assert len(entities) <= DEFAULT_LIST_LIMIT
        assert len(entities) == len(sample_models)

    @pytest.mark.asyncio
    async def test_list_all_with_limit(self, test_repository, sample_models):
        """Test listing entities with custom limit."""
        result = await test_repository.list_all(limit=2)
        entities = list(result.all())

        assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_list_all_with_offset(self, test_repository, sample_models):
        """Test listing entities with offset."""
        result = await test_repository.list_all(limit=2, offset=2)
        entities = list(result.all())

        assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_list_all_with_ordering(self, test_repository, sample_models):
        """Test listing entities with custom ordering."""
        result = await test_repository.list_all(order_by="value", descending=False)
        entities = list(result.all())

        values = [e.value for e in entities]
        assert values == sorted(values)

    @pytest.mark.asyncio
    async def test_list_all_with_filters(self, test_repository, sample_models):
        """Test listing entities with filters."""
        result = await test_repository.list_all(filters={"status": "active"})
        entities = list(result.all())

        assert all(e.status == "active" for e in entities)
        assert len(entities) == len(sample_models)

    @pytest.mark.asyncio
    async def test_list_all_limit_exceeds_maximum(self, test_repository):
        """Test that limit exceeding maximum raises ValueError."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            await test_repository.list_all(limit=MAX_LIST_LIMIT + 1)


# ============================================================================
# Bulk Operation Tests
# ============================================================================


class TestBulkOperations:
    """Tests for bulk operations."""

    @pytest.mark.asyncio
    async def test_create_many(self, test_repository, db_session):
        """Test creating multiple entities at once."""
        data = [{"name": f"bulk_{i}", "value": i, "status": "active"} for i in range(3)]
        entities = await test_repository.create_many(data)
        await db_session.flush()

        assert len(entities) == 3
        assert all(e.id is not None for e in entities)

    @pytest.mark.asyncio
    async def test_update_many(self, test_repository, sample_models):
        """Test updating multiple entities."""
        ids = [m.id for m in sample_models[:3]]
        count = await test_repository.update_many(ids, status="updated")

        assert count == 3

    @pytest.mark.asyncio
    async def test_update_many_empty_list(self, test_repository):
        """Test updating with empty ID list returns 0."""
        count = await test_repository.update_many([], status="updated")
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_many(self, test_repository, sample_models):
        """Test deleting multiple entities."""
        ids = [m.id for m in sample_models[:3]]
        count = await test_repository.delete_many(ids)

        assert count == 3

    @pytest.mark.asyncio
    async def test_refresh(self, test_repository, sample_models, db_session):
        """Test refreshing an entity."""
        model = sample_models[0]
        model.name = "modified_locally"

        refreshed = await test_repository.refresh(model)
        assert refreshed.name == model.name

    @pytest.mark.asyncio
    async def test_merge(self, test_repository, sample_models):
        """Test merging a detached entity."""
        model = sample_models[0]
        # Simulate detach by expiring
        await test_repository.session.expire(model)

        merged = await test_repository.merge(model)
        assert merged.id == model.id


# ============================================================================
# Soft Delete Tests
# ============================================================================


class TestSoftDelete:
    """Tests for soft delete functionality."""

    @pytest.mark.asyncio
    async def test_soft_delete_with_status_field(self, db_session, sample_models):
        """Test soft delete on model with status field."""
        from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase

        class TestSoftRepo(SQLAlchemyRepositoryBase[TestModel]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(session, TestModel)

        repo = TestSoftRepo(db_session)
        model = sample_models[0]

        result = await repo.soft_delete(model.id)

        assert result is not None
        assert result.status == "deleted"

    @pytest.mark.asyncio
    async def test_soft_delete_without_status_field(self, db_session):
        """Test soft delete on model without status field raises AttributeError."""
        from agent_comm_core.repositories.sqlalchemy_base import SQLAlchemyRepositoryBase

        class TestNoStatusRepo(SQLAlchemyRepositoryBase[TestModelWithoutStatus]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(session, TestModelWithoutStatus)

        repo = TestNoStatusRepo(db_session)
        model = TestModelWithoutStatus(name="test", value=1)
        db_session.add(model)
        await db_session.flush()

        with pytest.raises(AttributeError, match="does not have a 'status' field"):
            await repo.soft_delete(model.id)


# ============================================================================
# Helper Method Tests
# ============================================================================


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.mark.asyncio
    async def test_model_property(self, test_repository):
        """Test that model property returns correct model class."""
        assert test_repository.model is TestModel

    @pytest.mark.asyncio
    async def test_session_property(self, test_repository, db_session):
        """Test that session property returns correct session."""
        assert test_repository.session is db_session

    @pytest.mark.asyncio
    async def test_get_order_field_default(self, test_repository):
        """Test getting default order field."""
        field = test_repository._get_order_field(None)
        assert field == TestModel.created_at

    @pytest.mark.asyncio
    async def test_get_order_field_custom(self, test_repository):
        """Test getting custom order field."""
        field = test_repository._get_order_field("name")
        assert field == TestModel.name

    @pytest.mark.asyncio
    async def test_get_order_field_invalid_raises(self, test_repository):
        """Test that invalid order field raises AttributeError."""
        with pytest.raises(AttributeError, match="does not have field"):
            test_repository._get_order_field("invalid_field")


# ============================================================================
# Generic Type Tests
# ============================================================================


class TestGenericTypes:
    """Tests for generic type handling."""

    @pytest.mark.asyncio
    async def test_repository_preserves_model_type(self, test_repository):
        """Test that repository preserves model type information."""
        assert test_repository._model is TestModel

    @pytest.mark.asyncio
    async def test_create_returns_correct_type(self, test_repository):
        """Test that create returns the correct model type."""
        model = await test_repository.create(name="test", value=1, status="active")
        assert isinstance(model, TestModel)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_correct_type(self, test_repository, sample_models):
        """Test that get_by_id returns the correct model type."""
        model = sample_models[0]
        result = await test_repository.get_by_id(model.id)
        assert isinstance(result, TestModel)
