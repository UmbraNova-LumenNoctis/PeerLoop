from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)

    @model_validator(mode="after")
    def validate_prompt(self):
        """Validate that prompt content is not empty after trimming.
        
        Returns:
            Self: That prompt content is not empty after trimming.
        """
        if not self.prompt.strip():
            raise ValueError("Prompt cannot be empty")
        return self


class LLMChatResponse(BaseModel):
    provider: str = "google-gemini"
    model: str
    text: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    model_config = ConfigDict(from_attributes=True)


class LLMHistoryItem(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    provider: str | None = None
    model: str | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LLMHistoryDeleteResponse(BaseModel):
    deleted_count: int

    model_config = ConfigDict(from_attributes=True)
