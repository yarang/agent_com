"""
Decision models for recording agent decisions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DecisionStatus(str, Enum):
    """Status of a decision."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class DecisionBase(BaseModel):
    """Base decision model."""

    title: str = Field(..., description="Decision title", min_length=1, max_length=200)
    description: str = Field(
        ..., description="Detailed decision description", min_length=1, max_length=5000
    )
    context: dict = Field(default_factory=dict, description="Context and background")
    proposed_by: str = Field(..., description="Agent proposing the decision", min_length=1)
    options: list[dict[str, Any]] = Field(
        ..., description="Available options for the decision", min_length=1
    )
    deadline: Optional[datetime] = Field(default=None, description="Decision deadline")


class DecisionCreate(DecisionBase):
    """Model for creating a new decision."""

    meeting_id: Optional[UUID] = Field(default=None, description="Associated meeting ID if any")


class Decision(DecisionBase):
    """Complete decision model with database fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique decision ID")
    status: DecisionStatus = Field(
        default=DecisionStatus.PENDING, description="Current decision status"
    )
    meeting_id: Optional[UUID] = Field(default=None, description="Associated meeting ID")
    selected_option: Optional[dict[str, Any]] = Field(
        default=None, description="The option that was selected"
    )
    rationale: Optional[str] = Field(default=None, description="Rationale for the decision")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    decided_at: Optional[datetime] = Field(
        default=None, description="Timestamp when decision was made"
    )

    model_config = {"from_attributes": True}

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate options list."""
        if not v:
            raise ValueError("At least one option must be provided")
        for i, option in enumerate(v):
            if not isinstance(option, dict):
                raise ValueError(f"Option {i} must be a dictionary")
            if "title" not in option or not option["title"]:
                raise ValueError(f"Option {i} must have a title")
        return v

    @field_validator("selected_option")
    @classmethod
    def validate_selected_option(
        cls, v: Optional[dict[str, Any]], info
    ) -> Optional[dict[str, Any]]:
        """Validate selected option is in options."""
        if v is not None and "options" in info.data:
            options = info.data["options"]
            # Check if selected option matches one of the provided options
            option_titles = {opt.get("title") for opt in options}
            if v.get("title") not in option_titles:
                raise ValueError("Selected option must be one of the provided options")
        return v
