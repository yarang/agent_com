"""
LLM Provider abstraction for mediator system.

Provides unified interface for calling different LLM providers
(OpenAI, Anthropic, etc.) for mediator responses.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMRequest(BaseModel):
    """Request model for LLM generation."""

    system_prompt: str
    user_message: str
    temperature: float = 0.7
    max_tokens: int | None = None
    model_id: str
    api_endpoint: str | None = None
    additional_context: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    """Response model from LLM providers."""

    content: str
    model_used: str
    tokens_used: int | None = None
    finish_reason: str | None = None
    provider: str
    raw_response: dict[str, Any] | None = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers must implement the generate method.
    """

    provider_name: str = "base"

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            request: LLM request with prompt and parameters

        Returns:
            LLM response with generated content

        Raises:
            ValueError: If API key is not configured
            RuntimeError: If API call fails
        """
        pass

    def _get_api_key(self, env_var: str) -> str:
        """
        Get API key from environment.

        Args:
            env_var: Environment variable name

        Returns:
            API key value

        Raises:
            ValueError: If API key is not set
        """
        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"API key not configured. Set {env_var} environment variable.")
        return api_key


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider implementation.

    Supports GPT-4, GPT-3.5 Turbo, and other OpenAI models.
    """

    provider_name = "openai"

    def __init__(self) -> None:
        """Initialize OpenAI provider."""
        self.api_key = self._get_api_key("OPENAI_API_KEY")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using OpenAI API.

        Args:
            request: LLM request

        Returns:
            LLM response

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API call fails
        """
        try:
            # Import here to avoid hard dependency
            try:
                from openai import AsyncOpenAI
            except ImportError as err:
                raise RuntimeError(
                    "OpenAI package not installed. Install with: pip install openai"
                ) from err

            client = AsyncOpenAI(api_key=self.api_key)

            # Build messages
            messages = [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ]

            # Add context if provided
            if request.additional_context:
                context_str = self._format_context(request.additional_context)
                messages.insert(1, {"role": "system", "content": f"Context: {context_str}"})

            # Call API
            response = await client.chat.completions.create(
                model=request.model_id,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            # Extract response
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            finish_reason = response.choices[0].finish_reason

            return LLMResponse(
                content=content or "",
                model_used=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                provider=self.provider_name,
                raw_response={"id": response.id, "created": response.created},
            )

        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {str(e)}") from e

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format additional context for inclusion in prompt."""
        parts = []
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                import json

                parts.append(f"{key}: {json.dumps(value)}")
            else:
                parts.append(f"{key}: {value}")
        return "\n".join(parts)


class AnthropicProvider(LLMProvider):
    """
    Anthropic LLM provider implementation.

    Supports Claude 3 Opus, Sonnet, Haiku, and other Anthropic models.
    """

    provider_name = "anthropic"

    def __init__(self) -> None:
        """Initialize Anthropic provider."""
        self.api_key = self._get_api_key("ANTHROPIC_API_KEY")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using Anthropic API.

        Args:
            request: LLM request

        Returns:
            LLM response

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API call fails
        """
        try:
            # Import here to avoid hard dependency
            try:
                from anthropic import AsyncAnthropic
            except ImportError as err:
                raise RuntimeError(
                    "Anthropic package not installed. Install with: pip install anthropic"
                ) from err

            client = AsyncAnthropic(api_key=self.api_key)

            # Build prompt with context
            user_message = request.user_message
            if request.additional_context:
                context_str = self._format_context(request.additional_context)
                user_message = f"Context:\n{context_str}\n\n{user_message}"

            # Call API
            response = await client.messages.create(
                model=request.model_id,
                max_tokens=request.max_tokens or 4096,
                system=request.system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=request.temperature,
            )

            # Extract response
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            return LLMResponse(
                content=content,
                model_used=response.model,
                tokens_used=tokens_used,
                finish_reason=response.stop_reason,
                provider=self.provider_name,
                raw_response={"id": response.id},
            )

        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {str(e)}") from e

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format additional context for inclusion in prompt."""
        parts = []
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                import json

                parts.append(f"{key}: {json.dumps(value)}")
            else:
                parts.append(f"{key}: {value}")
        return "\n".join(parts)


class MockProvider(LLMProvider):
    """
    Mock LLM provider for testing.

    Returns predefined responses without making API calls.
    """

    provider_name = "mock"

    def __init__(self, response: str | None = None) -> None:
        """Initialize mock provider."""
        self.default_response = response or "This is a mock mediator response."

    async def generate(self, _request: LLMRequest) -> LLMResponse:
        """
        Generate mock response.

        Args:
            _request: LLM request (ignored)

        Returns:
            Mock LLM response
        """
        return LLMResponse(
            content=self.default_response,
            model_used="mock-model",
            tokens_used=None,
            finish_reason="stop",
            provider=self.provider_name,
            raw_response=None,
        )


def get_provider(provider_name: str) -> LLMProvider:
    """
    Get LLM provider instance by name.

    Args:
        provider_name: Name of the provider (openai, anthropic, mock)

    Returns:
        LLM provider instance

    Raises:
        ValueError: If provider is unknown
    """
    providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "mock": MockProvider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown provider: {provider_name}. Available providers: {', '.join(providers.keys())}"
        )

    return provider_class()
