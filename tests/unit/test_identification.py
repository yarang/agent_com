"""
Unit tests for project identification middleware.

This module tests the ProjectIdentificationMiddleware and related
functionality including API key prefix parsing, header extraction,
and project boundary validation.
"""

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from mcp_broker.core.context import RequestContext, get_request_context, set_request_context
from mcp_broker.core.identification import (
    ProjectIdentificationMiddleware,
    extract_project_id,
    get_project_from_request,
    verify_project_access,
)
from mcp_broker.models.project import (
    ProjectAPIKey,
    ProjectConfig,
    ProjectDefinition,
    ProjectMetadata,
)
from mcp_broker.project.registry import get_project_registry, reset_project_registry

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_registry():
    """Create a sample project registry with test projects."""
    from mcp_broker.project.registry import get_project_registry

    reset_project_registry()
    registry = get_project_registry()

    # Create test projects
    # Note: Project IDs should not contain underscores for proper API key parsing
    registry._projects["testproject"] = ProjectDefinition(
        project_id="testproject",
        metadata=ProjectMetadata(name="Test Project", description="A test project"),
        api_keys=[
            ProjectAPIKey(
                key_id="default",
                api_key="testproject_default_abcdefghijklmnopqrstuvwxyz123456",
                is_active=True,
            )
        ],
        config=ProjectConfig(),
    )

    registry._projects["anotherproject"] = ProjectDefinition(
        project_id="anotherproject",
        metadata=ProjectMetadata(name="Another Project", description="Another test project"),
        api_keys=[
            ProjectAPIKey(
                key_id="default",
                api_key="anotherproject_default_abcdefghijklmnopqrstuvwxyz123456",
                is_active=True,
            )
        ],
        config=ProjectConfig(),
    )

    # Default project
    registry._ensure_default_project()

    return registry


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""

    def _create_request(
        headers: dict | None = None,
        cookies: dict | None = None,
        query_params: dict | None = None,
        path: str = "/test",
    ):
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 12345),
        }

        request = Request(scope)

        # Set headers manually
        if headers:
            for key, value in headers.items():
                request.headers.__dict__["_list"].append((key.lower().encode(), value.encode()))

        # Set cookies manually
        if cookies:
            request._cookies = cookies

        # Set query params manually
        if query_params:
            from starlette.datastructures import QueryParams

            request._query_params = QueryParams(query_params)

        return request

    return _create_request


@pytest.fixture
def call_next_mock():
    """Create a mock call_next function for middleware."""

    async def _call_next(request: Request) -> Response:
        return JSONResponse(content={"status": "ok"})

    return _call_next


# =============================================================================
# API Key Prefix Parsing Tests
# =============================================================================


class TestAPIKeyPrefixParsing:
    """Tests for parsing project ID from API key prefix."""

    def test_parse_valid_api_key_prefix(self, sample_registry):
        """Test parsing a valid API key with project prefix."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        # Valid API key format: {project_id}_{key_id}_{secret}
        api_key = "testproject_default_abcdefghijklmnopqrstuvwxyz123456"
        result = middleware._parse_api_key_prefix(api_key)

        assert result == "testproject"

    def test_parse_api_key_with_underscores_in_secret(self, sample_registry):
        """Test parsing API key with underscores in the secret part."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        # API key with underscores in secret
        api_key = "myproject_keyid_secret_with_underscores"
        result = middleware._parse_api_key_prefix(api_key)

        assert result == "myproject"

    def test_parse_invalid_api_key_no_underscores(self, sample_registry):
        """Test parsing invalid API key without underscores."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        api_key = "invalidkey"
        result = middleware._parse_api_key_prefix(api_key)

        assert result is None

    def test_parse_invalid_api_key_only_one_underscore(self, sample_registry):
        """Test parsing invalid API key with only one underscore."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        api_key = "project_only"
        result = middleware._parse_api_key_prefix(api_key)

        assert result is None

    def test_parse_empty_api_key(self, sample_registry):
        """Test parsing empty API key."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        result = middleware._parse_api_key_prefix("")

        assert result is None


# =============================================================================
# Header Extraction Tests
# =============================================================================


class TestHeaderExtraction:
    """Tests for extracting project ID from headers."""

    @pytest.mark.asyncio
    async def test_extract_from_x_project_id_header(
        self, sample_registry, mock_request, call_next_mock
    ):
        """Test extracting project ID from X-Project-ID header."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(headers={"X-Project-ID": "testproject"})

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        assert request.state.project_id == "testproject"

    @pytest.mark.asyncio
    async def test_header_priority_over_api_key(
        self, sample_registry, mock_request, call_next_mock
    ):
        """Test that X-Project-ID header has priority over API key prefix."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(
            headers={
                "X-Project-ID": "anotherproject",
                "X-API-Key": "testproject_default_abcdefghijklmnopqrstuvwxyz123456",
            }
        )

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        # Header should take priority
        assert request.state.project_id == "anotherproject"


# =============================================================================
# API Key Extraction Tests
# =============================================================================


class TestAPIKeyExtraction:
    """Tests for extracting project ID from API key."""

    @pytest.mark.asyncio
    async def test_extract_from_api_key_header(self, sample_registry, mock_request, call_next_mock):
        """Test extracting project ID from X-API-Key header."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(
            headers={"X-API-Key": "testproject_default_abcdefghijklmnopqrstuvwxyz123456"}
        )

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        assert request.state.project_id == "testproject"

    @pytest.mark.asyncio
    async def test_extract_from_api_key_cookie(self, sample_registry, mock_request, call_next_mock):
        """Test extracting project ID from api_key cookie."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(
            cookies={"api_key": "testproject_default_abcdefghijklmnopqrstuvwxyz123456"}
        )

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        assert request.state.project_id == "testproject"


# =============================================================================
# Query Parameter Tests
# =============================================================================


class TestQueryParameterExtraction:
    """Tests for extracting project ID from query parameters."""

    @pytest.mark.asyncio
    async def test_extract_from_query_param(self, sample_registry, mock_request, call_next_mock):
        """Test extracting project ID from query parameter."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(query_params={"project_id": "testproject"})

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        assert request.state.project_id == "testproject"


# =============================================================================
# Fallback Behavior Tests
# =============================================================================


class TestFallbackBehavior:
    """Tests for default project fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_to_default_when_allowed(
        self, sample_registry, mock_request, call_next_mock
    ):
        """Test fallback to 'default' project when no identification found."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request()

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        assert request.state.project_id == "default"

    @pytest.mark.asyncio
    async def test_no_fallback_when_required(self, sample_registry, mock_request, call_next_mock):
        """Test that 401 is raised when identification is required but missing."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=True, allow_default_fallback=False
        )

        request = mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next_mock)

        assert exc_info.value.status_code == 401


# =============================================================================
# Public Endpoint Tests
# =============================================================================


class TestPublicEndpoints:
    """Tests for public endpoint bypass behavior."""

    @pytest.mark.asyncio
    async def test_public_endpoint_bypass(self, sample_registry, mock_request, call_next_mock):
        """Test that public endpoints skip identification."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=True, allow_default_fallback=False
        )

        # Test various public endpoints
        public_paths = ["/", "/health", "/docs", "/openapi.json"]

        for path in public_paths:
            request = mock_request(path=path)

            # Should not raise exception even without identification
            response = await middleware.dispatch(request, call_next_mock)

            assert response.status_code == 200


# =============================================================================
# Project Validation Tests
# =============================================================================


class TestProjectValidation:
    """Tests for project validation logic."""

    @pytest.mark.asyncio
    async def test_valid_project_accepted(self, sample_registry, mock_request, call_next_mock):
        """Test that valid project is accepted."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(headers={"X-Project-ID": "testproject"})

        response = await middleware.dispatch(request, call_next_mock)

        assert response.status_code == 200
        assert request.state.project_id == "testproject"

    @pytest.mark.asyncio
    async def test_invalid_project_rejected_when_required(
        self, sample_registry, mock_request, call_next_mock
    ):
        """Test that invalid project is rejected when identification is required."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=True, allow_default_fallback=False
        )

        request = mock_request(headers={"X-Project-ID": "nonexistent_project"})

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next_mock)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_inactive_project_rejected(self, sample_registry, mock_request, call_next_mock):
        """Test that inactive project is rejected."""
        registry = get_project_registry()
        project = registry._projects.get("testproject")
        if project:
            project.status.status = "inactive"

        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(headers={"X-Project-ID": "testproject"})

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next_mock)

        assert exc_info.value.status_code == 403

        # Reset status
        if project:
            project.status.status = "active"


# =============================================================================
# Request Context Tests
# =============================================================================


class TestRequestContext:
    """Tests for request context integration."""

    def test_set_and_get_context(self):
        """Test setting and getting request context."""
        context = RequestContext(
            project_id="testproject",
            security=None,
        )

        set_request_context(context)
        retrieved = get_request_context()

        assert retrieved.project_id == "testproject"

    def test_default_context_created(self):
        """Test that default context is created if none exists."""
        # Clear any existing context
        from mcp_broker.core.context import clear_request_context

        clear_request_context()

        # Get context should create default
        context = get_request_context()

        assert context.project_id == "default"
        assert context.is_authenticated is False


# =============================================================================
# Project Access Verification Tests
# =============================================================================


class TestProjectAccessVerification:
    """Tests for project boundary verification."""

    def test_same_project_access_allowed(self):
        """Test that same project access is always allowed."""
        result = verify_project_access("testproject", "testproject")

        assert result is True

    def test_cross_project_access_denied(self):
        """Test that cross-project access is denied by default."""
        result = verify_project_access("testproject", "anotherproject")

        assert result is False

    def test_cross_project_access_with_mismatch(self):
        """Test cross-project access with different projects."""
        result = verify_project_access("project_a", "project_b")

        assert result is False


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_extract_project_id_from_state(
        self, sample_registry, mock_request, call_next_mock
    ):
        """Test extract_project_id convenience function."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(headers={"X-Project-ID": "testproject"})

        await middleware.dispatch(request, call_next_mock)

        # Use convenience function
        project_id = await extract_project_id(request)

        assert project_id == "testproject"

    @pytest.mark.asyncio
    async def test_get_project_from_state(self, sample_registry, mock_request, call_next_mock):
        """Test get_project_from_request convenience function."""
        middleware = ProjectIdentificationMiddleware(
            app=None, require_identification=False, allow_default_fallback=True
        )

        request = mock_request(headers={"X-Project-ID": "testproject"})

        await middleware.dispatch(request, call_next_mock)

        # Use convenience function
        project = await get_project_from_request(request)

        assert project is not None
        assert project.project_id == "testproject"
