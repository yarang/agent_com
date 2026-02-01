"""
Unit tests for Security module.

Tests authentication middleware, token validation,
and security context.
"""

import os
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, status

from mcp_broker.core.config import BrokerConfig, get_config
from mcp_broker.core.security import (
    SecurityContext,
    SecurityMiddleware,
    generate_session_token,
    validate_session_token,
    verify_auth_token,
)


class TestSecurityMiddleware:
    """Tests for SecurityMiddleware class."""

    @pytest.fixture
    def mock_config(self) -> BrokerConfig:
        """Create test configuration."""
        return BrokerConfig(
            host="127.0.0.1",
            port=8000,
            log_level="DEBUG",
            storage_backend="memory",
            enable_auth=False,
        )

    @pytest.fixture
    def auth_config(self) -> BrokerConfig:
        """Create authenticated configuration."""
        return BrokerConfig(
            host="127.0.0.1",
            port=8000,
            log_level="DEBUG",
            storage_backend="memory",
            enable_auth=True,
            auth_secret="test_secret_key_12345",
        )

    @pytest.mark.asyncio
    async def test_public_endpoint_bypasses_auth(self, mock_config) -> None:
        """Test that public endpoints bypass authentication."""
        middleware = SecurityMiddleware(app=Mock())

        # Create mock request for public endpoint
        request = MagicMock(spec=Request)
        request.url.path = "/health"
        request.headers = {}
        request.cookies = {}

        call_next = AsyncMock(return_value=Mock())

        # Mock get_config to return our test config
        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: mock_config

        try:
            response = await middleware.dispatch(request, call_next)
            # Should pass through to next handler without auth check
            call_next.assert_called_once_with(request)
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_auth_disabled_bypasses_check(self, mock_config) -> None:
        """Test that disabled auth bypasses authentication."""
        middleware = SecurityMiddleware(app=Mock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/sessions"
        request.headers = {}
        request.cookies = {}
        request.client = "127.0.0.1"

        call_next = AsyncMock(return_value=Mock())

        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: mock_config

        try:
            response = await middleware.dispatch(request, call_next)
            call_next.assert_called_once_with(request)
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_valid_api_key_in_header(self, auth_config) -> None:
        """Test authentication with valid API key in header."""
        middleware = SecurityMiddleware(app=Mock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/sessions"
        request.headers = {"X-API-Key": "test_secret_key_12345"}
        request.cookies = {}
        request.client = "127.0.0.1"

        call_next = AsyncMock(return_value=Mock())

        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: auth_config

        try:
            response = await middleware.dispatch(request, call_next)
            call_next.assert_called_once_with(request)
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_valid_api_key_in_cookie(self, auth_config) -> None:
        """Test authentication with valid API key in cookie."""
        middleware = SecurityMiddleware(app=Mock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/sessions"
        request.headers = {}
        request.cookies = {"api_key": "test_secret_key_12345"}
        request.client = "127.0.0.1"

        call_next = AsyncMock(return_value=Mock())

        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: auth_config

        try:
            response = await middleware.dispatch(request, call_next)
            call_next.assert_called_once_with(request)
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_401(self, auth_config) -> None:
        """Test that missing API key raises 401 Unauthorized."""
        middleware = SecurityMiddleware(app=Mock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/sessions"
        request.headers = {}
        request.cookies = {}
        request.client = "127.0.0.1"

        call_next = AsyncMock(return_value=Mock())

        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: auth_config

        try:
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_403(self, auth_config) -> None:
        """Test that invalid API key raises 403 Forbidden."""
        middleware = SecurityMiddleware(app=Mock())

        request = MagicMock(spec=Request)
        request.url.path = "/api/sessions"
        request.headers = {"X-API-Key": "wrong_secret_key"}
        request.cookies = {}
        request.client = "127.0.0.1"

        call_next = AsyncMock(return_value=Mock())

        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: auth_config

        try:
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        finally:
            security_module.get_config = original_get_config


class TestVerifyAuthToken:
    """Tests for verify_auth_token function."""

    @pytest.fixture
    def auth_config(self) -> BrokerConfig:
        """Create authenticated configuration."""
        return BrokerConfig(
            host="127.0.0.1",
            port=8000,
            log_level="DEBUG",
            storage_backend="memory",
            enable_auth=True,
            auth_secret="test_secret_key_12345",
        )

    @pytest.mark.asyncio
    async def test_verify_with_auth_disabled(self) -> None:
        """Test verification returns True when auth is disabled."""
        config = BrokerConfig(enable_auth=False)

        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: config

        try:
            request = MagicMock(spec=Request)
            request.headers = {}
            request.cookies = {}

            result = await verify_auth_token(request)
            assert result is True
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_verify_with_valid_token(self, auth_config) -> None:
        """Test verification with valid token."""
        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: auth_config

        try:
            request = MagicMock(spec=Request)
            request.headers = {"X-API-Key": "test_secret_key_12345"}
            request.cookies = {}

            result = await verify_auth_token(request)
            assert result is True
        finally:
            security_module.get_config = original_get_config

    @pytest.mark.asyncio
    async def test_verify_with_invalid_token(self, auth_config) -> None:
        """Test verification with invalid token."""
        import mcp_broker.core.security as security_module
        original_get_config = security_module.get_config
        security_module.get_config = lambda: auth_config

        try:
            request = MagicMock(spec=Request)
            request.headers = {"X-API-Key": "wrong_token"}
            request.cookies = {}

            result = await verify_auth_token(request)
            assert result is False
        finally:
            security_module.get_config = original_get_config


class TestGenerateSessionToken:
    """Tests for generate_session_token function."""

    def test_generate_token_length(self) -> None:
        """Test that generated tokens have expected length."""
        token = generate_session_token()
        # base64url encoding of 32 bytes = 43 characters
        assert len(token) == 43

    def test_generate_token_unique(self) -> None:
        """Test that generated tokens are unique."""
        token1 = generate_session_token()
        token2 = generate_session_token()
        assert token1 != token2

    def test_generate_token_valid_chars(self) -> None:
        """Test that generated tokens only use valid characters."""
        token = generate_session_token()
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        )
        assert all(c in valid_chars for c in token)


class TestValidateSessionToken:
    """Tests for validate_session_token function."""

    def test_validate_valid_token(self) -> None:
        """Test validation of valid token."""
        token = generate_session_token()
        assert validate_session_token(token) is True

    def test_validate_empty_token(self) -> None:
        """Test validation of empty token."""
        assert validate_session_token("") is False

    def test_validate_short_token(self) -> None:
        """Test validation of short token."""
        assert validate_session_token("abc") is False

    def test_validate_token_with_invalid_chars(self) -> None:
        """Test validation of token with invalid characters."""
        assert validate_session_token("token with spaces!") is False


class TestSecurityContext:
    """Tests for SecurityContext class."""

    def test_default_context(self) -> None:
        """Test default security context."""
        context = SecurityContext()
        assert context.authenticated is False
        assert context.session_id is None
        assert context.is_authenticated() is False

    def test_authenticated_context(self) -> None:
        """Test authenticated security context."""
        session_id = uuid4()
        context = SecurityContext(authenticated=True, session_id=session_id)
        assert context.authenticated is True
        assert context.session_id == session_id
        assert context.is_authenticated() is True

    def test_context_age(self) -> None:
        """Test security context age calculation."""
        import time

        context = SecurityContext(authenticated=True)
        age = context.age_seconds()
        assert age >= 0
        assert age < 1  # Should be very recent

    def test_context_age_increases(self) -> None:
        """Test that context age increases over time."""
        import time

        context = SecurityContext(authenticated=True)
        age1 = context.age_seconds()
        time.sleep(0.01)
        age2 = context.age_seconds()
        assert age2 > age1
