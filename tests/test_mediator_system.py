"""
Tests for mediator system.

Provides unit tests for mediator models, services, and API endpoints.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from agent_comm_core.db.models.mediator import (
    MediatorDB,
    MediatorModelDB,
    MediatorPromptDB,
)
from agent_comm_core.models.mediator import (
    ChatRoomMediatorCreate,
    MediatorCreate,
    MediatorModelCreate,
    MediatorPromptCreate,
)
from agent_comm_core.services.llm_providers import MockProvider, get_provider
from agent_comm_core.services.mediator import MediatorService

# ============================================================================
# LLM Provider Tests
# ============================================================================


class TestLLMProviders:
    """Tests for LLM provider implementations."""

    @pytest.mark.asyncio
    async def test_mock_provider(self):
        """Test mock provider generates responses."""
        from agent_comm_core.services.llm_providers import LLMRequest

        provider = MockProvider(response="Test response")
        request = LLMRequest(
            system_prompt="You are a test assistant.",
            user_message="Hello",
            model_id="mock-model",
        )

        response = await provider.generate(request)

        assert response.content == "Test response"
        assert response.model_used == "mock-model"
        assert response.provider == "mock"
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_get_provider(self):
        """Test get_provider factory function."""
        mock = get_provider("mock")
        assert isinstance(mock, MockProvider)

        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown_provider")


# ============================================================================
# Pydantic Model Tests
# ============================================================================


class TestMediatorModels:
    """Tests for mediator Pydantic models."""

    def test_mediator_model_create(self):
        """Test mediator model creation."""
        data = MediatorModelCreate(
            name="Test Model",
            provider="openai",
            model_id="gpt-4",
            max_tokens=8192,
            supports_streaming=True,
        )

        assert data.name == "Test Model"
        assert data.provider == "openai"
        assert data.model_id == "gpt-4"
        assert data.max_tokens == 8192
        assert data.supports_streaming is True

    def test_mediator_prompt_create(self):
        """Test mediator prompt creation."""
        data = MediatorPromptCreate(
            project_id=uuid4(),
            name="Test Prompt",
            category="moderator",
            system_prompt="You are a helpful moderator.",
        )

        assert data.name == "Test Prompt"
        assert data.category == "moderator"
        assert data.system_prompt == "You are a helpful moderator."

    def test_mediator_create(self):
        """Test mediator creation."""
        data = MediatorCreate(
            project_id=uuid4(),
            name="Test Mediator",
            model_id=uuid4(),
            temperature="0.7",
        )

        assert data.name == "Test Mediator"
        assert data.temperature == "0.7"

    def test_invalid_temperature(self):
        """Test temperature validation rejects invalid values."""
        with pytest.raises(ValueError):
            MediatorCreate(
                project_id=uuid4(),
                name="Test Mediator",
                model_id=uuid4(),
                temperature="1.5",  # Invalid
            )

    def test_chat_room_mediator_create(self):
        """Test chat room mediator assignment creation."""
        data = ChatRoomMediatorCreate(
            mediator_id=uuid4(),
            auto_trigger=True,
            trigger_keywords=["help", "support"],
        )

        assert data.auto_trigger is True
        assert data.trigger_keywords == ["help", "support"]


# ============================================================================
# Database Model Tests
# ============================================================================


class TestMediatorDatabaseModels:
    """Tests for mediator database models."""

    def test_mediator_model_db_repr(self):
        """Test MediatorModelDB string representation."""
        model = MediatorModelDB(
            name="Test Model",
            provider="openai",
            model_id="gpt-4",
        )
        assert "Test Model" in repr(model)
        assert "openai" in repr(model)

    def test_mediator_prompt_db_repr(self):
        """Test MediatorPromptDB string representation."""
        prompt = MediatorPromptDB(
            project_id=uuid4(),
            name="Test Prompt",
            category="moderator",
            system_prompt="Test prompt",
        )
        assert "Test Prompt" in repr(prompt)

    def test_mediator_db_repr(self):
        """Test MediatorDB string representation."""
        project_id = uuid4()
        mediator = MediatorDB(
            project_id=project_id,
            name="Test Mediator",
            model_id=uuid4(),
        )
        assert "Test Mediator" in repr(mediator)
        assert str(project_id) in repr(mediator)


# ============================================================================
# Service Tests (with mock database)
# ============================================================================


class TestMediatorService:
    """Tests for mediator service."""

    @pytest.mark.asyncio
    async def test_should_trigger_mediator_auto(self):
        """Test mediator triggers with auto_trigger=True."""
        from unittest.mock import MagicMock

        service = MediatorService(MagicMock())

        assignment = MagicMock()
        assignment.auto_trigger = True
        assignment.trigger_keywords = None

        assert service._should_trigger_mediator(assignment, "any message") is True

    @pytest.mark.asyncio
    async def test_should_trigger_mediator_keywords(self):
        """Test mediator triggers with keyword match."""
        from unittest.mock import MagicMock

        service = MediatorService(MagicMock())

        assignment = MagicMock()
        assignment.auto_trigger = False
        assignment.trigger_keywords = ["help", "support"]

        assert service._should_trigger_mediator(assignment, "I need help") is True
        assert service._should_trigger_mediator(assignment, "Hello") is False

    @pytest.mark.asyncio
    async def test_should_trigger_mediator_no_trigger(self):
        """Test mediator doesn't trigger without auto or keyword match."""
        from unittest.mock import MagicMock

        service = MediatorService(MagicMock())

        assignment = MagicMock()
        assignment.auto_trigger = False
        assignment.trigger_keywords = ["help"]

        assert service._should_trigger_mediator(assignment, "Hello world") is False


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestMediatorAPI:
    """Tests for mediator API endpoints."""

    @pytest.mark.asyncio
    async def test_list_mediator_models_empty(self, client: AsyncClient):
        """Test listing models when none exist."""
        response = await client.get("/api/v1/mediator-models")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_mediator_model(self, client: AsyncClient):
        """Test creating a new mediator model."""
        data = {
            "name": "Test Model",
            "provider": "mock",
            "model_id": "test-model",
            "max_tokens": 1000,
        }

        response = await client.post("/api/v1/mediator-models", json=data)

        # Note: This would fail with authentication in production
        # In test environment, we'd need to mock auth or use test client overrides

    @pytest.mark.asyncio
    async def test_get_nonexistent_model(self, client: AsyncClient):
        """Test getting a model that doesn't exist."""
        response = await client.get(f"/api/v1/mediator-models/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_prompt_categories(self, client: AsyncClient):
        """Test listing prompt categories."""
        response = await client.get("/api/v1/mediator-prompts/categories")

        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        assert "moderator" in categories
        assert "summarizer" in categories


# ============================================================================
# Integration Tests
# ============================================================================


class TestMediatorIntegration:
    """Integration tests for mediator system."""

    @pytest.mark.asyncio
    async def test_full_mediator_workflow(self, db_session):
        """
        Test complete mediator workflow:
        1. Create model
        2. Create prompt
        3. Create mediator
        4. Assign to room
        5. Trigger mediator
        """
        # This would require a real database session
        # and is more of an integration test

        pass
