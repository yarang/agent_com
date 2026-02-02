"""
Mediator system Pydantic models for API.

Provides request/response models for mediator CRUD operations,
model management, and prompt management.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MediatorModelProvider(str, Enum):
    """LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    CUSTOM = "custom"


class MediatorPromptCategory(str, Enum):
    """Prompt categories for different use cases."""

    MODERATOR = "moderator"
    SUMMARIZER = "summarizer"
    FACILITATOR = "facilitator"
    TRANSLATOR = "translator"
    CODE_REVIEWER = "code_reviewer"
    TECHNICAL_ADVISOR = "technical_advisor"
    CUSTOM = "custom"


# ============================================================================
# Mediator Model Management
# ============================================================================


class MediatorModelCreate(BaseModel):
    """Request model for creating a new mediator model."""

    name: str = Field(..., min_length=1, max_length=100, description="Model name")
    provider: MediatorModelProvider = Field(..., description="LLM provider")
    model_id: str = Field(..., min_length=1, max_length=100, description="API model identifier")
    api_endpoint: str | None = Field(None, max_length=255, description="Custom API endpoint")
    max_tokens: int | None = Field(None, gt=0, description="Maximum tokens supported")
    supports_streaming: bool = Field(default=False, description="Supports streaming responses")
    supports_function_calling: bool = Field(default=False, description="Supports function calling")
    cost_per_1k_tokens: str | None = Field(
        None, max_length=20, description="Cost per 1k tokens (USD)"
    )


class MediatorModelUpdate(BaseModel):
    """Request model for updating a mediator model."""

    name: str | None = Field(None, min_length=1, max_length=100)
    api_endpoint: str | None = Field(None, max_length=255)
    max_tokens: int | None = Field(None, gt=0)
    supports_streaming: bool | None = None
    supports_function_calling: bool | None = None
    cost_per_1k_tokens: str | None = Field(None, max_length=20)
    is_active: bool | None = None


class MediatorModelResponse(BaseModel):
    """Response model for mediator model."""

    id: UUID
    name: str
    provider: str
    model_id: str
    api_endpoint: str | None
    max_tokens: int | None
    supports_streaming: bool
    supports_function_calling: bool
    cost_per_1k_tokens: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Mediator Prompt Management
# ============================================================================


class MediatorPromptCreate(BaseModel):
    """Request model for creating a new mediator prompt."""

    project_id: UUID = Field(..., description="Project ID")
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    description: str | None = Field(None, description="Prompt description")
    category: MediatorPromptCategory = Field(..., description="Prompt category")
    system_prompt: str = Field(..., min_length=1, description="System prompt content")
    variables: dict[str, Any] | None = Field(None, description="Configurable variables")
    examples: dict[str, Any] | None = Field(None, description="Few-shot examples")
    is_public: bool = Field(default=False, description="Share across project")

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        """Validate system prompt length."""
        if len(v) > 100000:
            raise ValueError("System prompt exceeds maximum length of 100,000 characters")
        return v


class MediatorPromptUpdate(BaseModel):
    """Request model for updating a mediator prompt."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: MediatorPromptCategory | None = None
    system_prompt: str | None = Field(None, min_length=1)
    variables: dict[str, Any] | None = None
    examples: dict[str, Any] | None = None
    is_public: bool | None = None
    is_active: bool | None = None


class MediatorPromptResponse(BaseModel):
    """Response model for mediator prompt."""

    id: UUID
    project_id: UUID
    name: str
    description: str | None
    category: str
    system_prompt: str
    variables: dict[str, Any] | None
    examples: dict[str, Any] | None
    is_public: bool
    is_active: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MediatorPromptDuplicate(BaseModel):
    """Request model for duplicating a prompt."""

    name: str = Field(..., min_length=1, max_length=255, description="New prompt name")


# ============================================================================
# Mediator Management
# ============================================================================


class MediatorCreate(BaseModel):
    """Request model for creating a new mediator."""

    project_id: UUID = Field(..., description="Project ID")
    name: str = Field(..., min_length=1, max_length=255, description="Mediator name")
    description: str | None = Field(None, description="Mediator description")
    model_id: UUID = Field(..., description="LLM model ID")
    default_prompt_id: UUID | None = Field(None, description="Default prompt ID")
    system_prompt: str | None = Field(None, description="System prompt override")
    temperature: str | None = Field(
        None, pattern=r"^0?\.\d+$|^1\.0$", description="Temperature (0.0-1.0)"
    )
    max_tokens: int | None = Field(None, gt=0, le=128000, description="Max tokens")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: str | None) -> str | None:
        """Validate temperature value."""
        if v is not None:
            try:
                temp = float(v)
                if not 0.0 <= temp <= 1.0:
                    raise ValueError("Temperature must be between 0.0 and 1.0")
            except ValueError as e:
                raise ValueError("Invalid temperature format") from e
        return v


class MediatorUpdate(BaseModel):
    """Request model for updating a mediator."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    model_id: UUID | None = None
    default_prompt_id: UUID | None = None
    system_prompt: str | None = None
    temperature: str | None = Field(None, pattern=r"^0?\.\d+$|^1\.0$")
    max_tokens: int | None = Field(None, gt=0, le=128000)
    is_active: bool | None = None


class MediatorResponse(BaseModel):
    """Response model for mediator."""

    id: UUID
    project_id: UUID
    name: str
    description: str | None
    model_id: UUID
    default_prompt_id: UUID | None
    system_prompt: str | None
    temperature: str | None
    max_tokens: int | None
    is_active: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MediatorDetailResponse(MediatorResponse):
    """Detailed response model for mediator including related data."""

    model: MediatorModelResponse | None = None
    default_prompt: MediatorPromptResponse | None = None


# ============================================================================
# Chat Room Mediator Assignment
# ============================================================================


class ChatRoomMediatorCreate(BaseModel):
    """Request model for assigning a mediator to a chat room."""

    mediator_id: UUID = Field(..., description="Mediator ID")
    prompt_id: UUID | None = Field(None, description="Override prompt ID")
    is_active: bool = Field(default=True, description="Assignment status")
    auto_trigger: bool = Field(default=False, description="Auto-trigger on every message")
    trigger_keywords: list[str] | None = Field(None, description="Keywords that trigger mediator")

    @field_validator("trigger_keywords")
    @classmethod
    def validate_trigger_keywords(cls, v: list[str] | None) -> list[str] | None:
        """Validate trigger keywords."""
        if v is not None:
            if len(v) > 50:
                raise ValueError("Maximum 50 trigger keywords allowed")
            # Validate each keyword
            for keyword in v:
                if not keyword or len(keyword) > 100:
                    raise ValueError("Each keyword must be 1-100 characters")
        return v


class ChatRoomMediatorUpdate(BaseModel):
    """Request model for updating chat room mediator assignment."""

    prompt_id: UUID | None = None
    is_active: bool | None = None
    auto_trigger: bool | None = None
    trigger_keywords: list[str] | None = None


class ChatRoomMediatorResponse(BaseModel):
    """Response model for chat room mediator assignment."""

    id: UUID
    room_id: UUID
    mediator_id: UUID
    prompt_id: UUID | None
    is_active: bool
    auto_trigger: bool
    trigger_keywords: list[str] | None
    joined_at: datetime

    model_config = {"from_attributes": True}


class ChatRoomMediatorDetailResponse(ChatRoomMediatorResponse):
    """Detailed response model for chat room mediator assignment."""

    mediator: MediatorResponse | None = None
    prompt_override: MediatorPromptResponse | None = None


# ============================================================================
# Mediator Processing
# ============================================================================


class MediatorTriggerRequest(BaseModel):
    """Request model for manually triggering a mediator."""

    message_content: str = Field(..., min_length=1, description="Message content to process")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class MediatorResponse(BaseModel):
    """Response model for mediator output."""

    mediator_id: UUID
    room_id: UUID
    response: str
    processed_at: datetime
    tokens_used: int | None = None
    model_used: str | None = None


class MediatorMessageContext(BaseModel):
    """Context provided to mediator for processing."""

    room_id: UUID
    message_content: str
    sender_id: str | None = None
    message_history: list[dict[str, Any]] | None = None
    room_participants: list[str] | None = None
    additional_context: dict[str, Any] | None = None
